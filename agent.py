# See /docs_imported/agents/building-voice-agents.md - Voice AI agent setup
import contextlib
import os
import sys
import asyncio
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import (
    AgentSession,
    Agent,
    RoomInputOptions,
    JobContext,
    WorkerOptions,
    cli,
    BackgroundAudioPlayer,
    AudioConfig,
    BuiltinAudioClip,
)
from livekit.plugins import google, noise_cancellation
from prompts import AGENT_INSTRUCTIONS, SESSION_INSTRUCTION
from tools.weather import get_weather
from tools.search import search_web
from tools.send_email import send_email
from tools.net_health import check_network_health
from tools.shutdown import shutdown_agent, set_memory_manager
from tools.generate_password import generate_password
from memory import MemoryManager, MemoryConfig
import logging

load_dotenv()
logger = logging.getLogger(__name__)

ENABLE_THINKING_AUDIO = os.getenv("ENABLE_THINKING_AUDIO", "false").lower() == "true"
# Conservative default volumes to avoid masking speech when thinking audio is enabled.
# See https://docs.livekit.io/agents/build/audio/#adding-background-audio - Background audio guidance
THINKING_VOLUME_1 = float(os.getenv("THINKING_VOLUME_1", "0.3"))
THINKING_VOLUME_2 = float(os.getenv("THINKING_VOLUME_2", "0.2"))

# Global flag for hard shutdown detection
_shutdown_requested = False

# See /docs_imported/agents/building-voice-agents.md - Agent class with Gemini realtime model
class JarvisAgent(Agent):
    """JARVIS voice assistant using Google Gemini Realtime Model.
    
    This agent provides a sophisticated butler-like AI personality with
    real-time voice interactions and tool capabilities (weather, web search).
    Uses Google's Gemini for end-to-end speech-to-speech processing.
    """
    
    def __init__(self):
        super().__init__(
            instructions=AGENT_INSTRUCTIONS,
            llm=google.beta.realtime.RealtimeModel(
                voice="Charon",   # Gemini voice (text-to-speech)
                temperature=0.7  # Tweak for desired creativity
            ),
            tools=[
                get_weather,
                search_web,
                send_email,
                check_network_health,
                shutdown_agent,
                generate_password,  # Secure password generation tool
            ]
        )

# See /docs_imported/agents/building-voice-agents.md - AgentSession setup and entrypoint
async def entrypoint(ctx: JobContext) -> None:
    """Main entry point for JARVIS agent worker.
    
    Sets up the agent session with noise cancellation, memory system, and starts
    the voice interaction loop when a participant joins the room.
    Includes error handling for realtime API timeouts and memory lifecycle.
    
    Memory Lifecycle:
    1. Initialize memory manager and load past context
    2. Buffer messages during session
    3. Flush session to mem0 on shutdown
    
    Args:
        ctx: JobContext containing room connection and participant info
    """
    # Initialize memory manager
    memory_config = MemoryConfig()
    memory_manager = MemoryManager(config=memory_config)
    
    # Enhanced startup logging
    logger.info("=" * 60)
    logger.info("🤖 ASTRO AGENT INITIALIZATION")
    logger.info("=" * 60)
    logger.info(f"📅 Date: {datetime.now().strftime('%B %d, %Y %I:%M %p')}")
    logger.info(f"🆔 Session ID: {memory_manager.session_id}")
    logger.info(f"📂 DB Path: {memory_manager.config.chroma_path}")
    
    await memory_manager.initialize()
    
    # Log memory status after initialization
    if memory_manager.config.enable_memory:
        logger.info(f"✅ Memory: ENABLED")
        logger.info(f"🧠 Loaded Memories: {len(memory_manager.loaded_memories)}")
    else:
        logger.warning("⚠️  Memory: DISABLED - no persistence between sessions!")
    
    logger.info(f"🎤 Voice: Gemini Realtime (Charon)")
    logger.info(f"🔧 Tools: weather, search, email, network_health, shutdown, generate_password")
    logger.info("=" * 60)
    
    # Register memory manager with shutdown tool
    set_memory_manager(memory_manager)
    
    # Using Gemini realtime model for full speech-to-speech pipeline
    # STT, LLM, and TTS are all handled by the RealtimeModel in JarvisAgent
    session = AgentSession()
    await ctx.connect()
    background_audio: Optional[BackgroundAudioPlayer] = None

    try:
        background_audio = await _start_session_with_feedback(ctx, session, memory_manager)
        
        # Keep the session alive by waiting indefinitely until:
        # 1. User disconnects from room
        # 2. Shutdown tool is called (triggers os._exit)
        # 3. Error occurs
        while not _shutdown_requested:
            await asyncio.sleep(0.5)  # Check every 0.5 seconds
        
    except agents.llm.realtime.RealtimeError as e:
        logger.error(f"Realtime API error: {e}")
        # Attempt graceful recovery or restart
        logger.info("Attempting to restart agent session...")
        try:
            with contextlib.suppress(Exception):
                if background_audio:
                    await background_audio.aclose()
            background_audio = await _start_session_with_feedback(ctx, session, memory_manager)
            while not _shutdown_requested:
                await asyncio.sleep(0.5)
        except Exception as retry_err:
            logger.error(f"Failed to restart session: {retry_err}")
    except Exception as e:
        logger.error(f"Unexpected error in entrypoint: {e}", exc_info=True)
    finally:
        # Only run cleanup if NOT shutdown tool (shutdown tool handles its own cleanup)
        if not _shutdown_requested:
            # Shutdown sequence: flush memory, close resources
            logger.info("=" * 60)
            logger.info("🛑 ASTRO AGENT SHUTDOWN (USER DISCONNECT)")
            logger.info("=" * 60)
            
            if background_audio:
                with contextlib.suppress(Exception):
                    await background_audio.aclose()
            
            # CRITICAL: Flush session memory BEFORE exit (give it time!)
            if memory_manager and memory_manager.config.enable_memory:
                try:
                    session_duration = (datetime.now() - memory_manager.session_start_time).total_seconds()
                    logger.info(f"💾 Flushing {len(memory_manager.session_messages)} session messages")
                    logger.info(f"⏱️  Session duration: {session_duration:.1f}s")
                    logger.info("⏳ Waiting for memory extraction to complete...")
                    
                    # CRITICAL FIX: Wait for flush to complete (can take 5-10 seconds)
                    flush_success = await asyncio.wait_for(
                        memory_manager.flush_session(),
                        timeout=30.0  # Give mem0 enough time to extract and save
                    )
                    
                    if flush_success:
                        logger.info("✅ Memory flushed successfully")
                    else:
                        logger.warning("⚠️  Memory flush failed - check logs above for details")
                    
                    await memory_manager.close()
                    logger.info("✅ Resources closed")
                except asyncio.TimeoutError:
                    logger.error("❌ Memory flush TIMED OUT after 30s - memories may be lost!")
                    logger.error("   Consider increasing timeout or checking API connectivity")
                except Exception as e:
                    logger.error(f"❌ Error flushing memory on shutdown: {e}", exc_info=True)
            
            logger.info("=" * 60)
            logger.info("👋 ASTRO shutdown complete")

# See https://docs.livekit.io/agents/build/external-data/#user-feedback - Status updates and thinking cues during tool execution
# See https://docs.livekit.io/agents/build/audio/#adding-background-audio - BackgroundAudioPlayer usage
async def _start_session_with_feedback(
    ctx: JobContext,
    session: AgentSession,
    memory_manager: MemoryManager,
) -> Optional[BackgroundAudioPlayer]:
    """Start the session and conditionally attach thinking audio.
    
    Loads past memory context and injects it into session instructions
    to enable continuity across sessions. Hooks into conversation events
    to capture messages for memory storage.
    
    Args:
        ctx: JobContext with room connection
        session: AgentSession to configure
        memory_manager: MemoryManager with loaded past context
        
    Returns:
        BackgroundAudioPlayer instance or None if disabled
    """
    global _shutdown_requested
    
    # See /docs_imported/agents/events.md - conversation_item_added event for message capture
    @session.on("conversation_item_added")
    def on_conversation_item_added(event):
        """Capture conversation messages and buffer them in memory manager.
        
        Filters out system messages and injected memory context to avoid pollution.
        Only user and assistant messages are buffered for later extraction.
        """
        item = event.item
        # Extract text content from message
        text_content = item.text_content if hasattr(item, 'text_content') else str(item.content)
        
        # Add to memory buffer (manager filters out system/injected content)
        memory_manager.add_message(
            role=item.role,
            content=text_content
        )
        logger.debug(f"Buffered message in memory: {item.role} - {text_content[:50]}...")
    
    # See /docs_imported/agents/events.md - function_calls_collected event for tool execution
    @session.on("function_calls_collected")
    def on_function_calls_collected(event):
        """Detect shutdown tool calls for hard termination after response.
        
        When shutdown_agent tool is called, we set a flag and schedule
        os._exit(0) to execute after the agent speaks the goodbye message.
        This ensures clean memory flush and proper farewell before termination.
        """
        global _shutdown_requested
        for call_info in event.function_calls:
            # Validate call_info has required attributes
            if not hasattr(call_info, 'function_info') or not call_info.function_info:
                logger.warning(f"Skipping invalid function call without function_info")
                continue
            
            if not hasattr(call_info.function_info, 'name'):
                logger.warning(f"Skipping function call without name attribute")
                continue
                
            if call_info.function_info.name == "shutdown_agent":
                logger.info("Shutdown tool detected - will execute hard shutdown after response")
                _shutdown_requested = True
                # Schedule hard exit after a short delay to allow goodbye message
                asyncio.create_task(_delayed_hard_shutdown())
    
    # See https://docs.livekit.io/agents/build/events/#close - Session close event
    # NOTE: Must be synchronous callback; use asyncio.create_task for async work
    def _auto_flush_on_session_close(event):
        """Auto-flush memory when user disconnects (not just on shutdown tool).
        
        This hook ensures memory is saved whenever the session ends, whether due to:
        - User closing browser/app
        - Network disconnection
        - Room deletion
        - Unrecoverable error
        
        Synchronous wrapper that schedules async flush as a task.
        """
        logger.info("=" * 60)
        logger.info("📊 SESSION CLOSED - Flushing memory (automatic)")
        logger.info("=" * 60)
        
        # Schedule async flush as a background task
        asyncio.create_task(_async_flush_on_close())
    
    async def _async_flush_on_close():
        """Async helper to flush memory after session close."""
        if memory_manager and memory_manager.config.enable_memory:
            try:
                session_duration = (datetime.now() - memory_manager.session_start_time).total_seconds()
                logger.info(f"💾 Flushing {len(memory_manager.session_messages)} session messages")
                logger.info(f"⏱️  Session duration: {session_duration:.1f}s")
                logger.info("⏳ Waiting for memory extraction to complete...")
                
                # Wait for flush to complete (same 30s timeout as manual shutdown)
                flush_success = await asyncio.wait_for(
                    memory_manager.flush_session(),
                    timeout=30.0
                )
                
                if flush_success:
                    logger.info("✅ Memory auto-flushed successfully on disconnect")
                else:
                    logger.warning("⚠️  Memory auto-flush returned False - check logs above")
                
                await memory_manager.close()
                logger.info("✅ Memory manager closed")
            except asyncio.TimeoutError:
                logger.error("❌ Memory auto-flush TIMED OUT after 30s!")
            except Exception as e:
                logger.error(f"❌ Error in session close handler: {e}", exc_info=True)
    
    @session.on("close")
    def on_session_close(event):
        """Wrapper for auto-flush on session close."""
        _auto_flush_on_session_close(event)
    
    await session.start(
        room=ctx.room,
        agent=JarvisAgent(),
        room_input_options=RoomInputOptions(
            video_enabled=False,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    background_audio: Optional[BackgroundAudioPlayer] = None
    if ENABLE_THINKING_AUDIO:
        logger.info("background-audio: ENABLE_THINKING_AUDIO=true; starting player")
        background_audio = BackgroundAudioPlayer(
            thinking_sound=[
                # See https://docs.livekit.io/agents/build/audio/#adding-background-audio
                # Lower volumes recommended for voice agents; tune via env THINKING_VOLUME_* if needed
                AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=THINKING_VOLUME_1),
                AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=THINKING_VOLUME_2),
            ],
        )
        await background_audio.start(room=ctx.room, agent_session=session)
    else:
        logger.info("background-audio: ENABLE_THINKING_AUDIO=false; not starting player")

    # Get past memory context and inject into instructions
    past_context = memory_manager.get_loaded_context()
    session_instruction_with_memory = SESSION_INSTRUCTION
    if past_context:
        session_instruction_with_memory = (
            f"{SESSION_INSTRUCTION}\n\n"
            f"**Previous Conversation Context:**\n{past_context}\n\n"
            f"Use this context to personalize responses and remember user preferences."
        )
        logger.info(f"Loaded {len(memory_manager.loaded_memories)} memories from previous sessions")

    await session.generate_reply(instructions=session_instruction_with_memory)
    return background_audio


async def _delayed_hard_shutdown():
    """Execute hard shutdown after allowing time for agent to speak goodbye.
    
    Waits 5 seconds to ensure the goodbye message is spoken, then calls os._exit(0)
    for complete process termination (no restart, no respawn).
    """
    logger.critical("=" * 60)
    logger.critical("🛑 HARD SHUTDOWN SEQUENCE INITIATED")
    logger.critical("⏳ Waiting 5 seconds for goodbye message...")
    logger.critical("=" * 60)
    
    await asyncio.sleep(5)  # Increased from 3s to ensure TTS completes
    
    logger.critical("=" * 60)
    logger.critical("🛑 EXECUTING HARD SHUTDOWN WITH os._exit(0)")
    logger.critical("📋 Exit code: 0 (clean shutdown)")
    logger.critical("🚫 NO RESTART SHOULD OCCUR")
    logger.critical("=" * 60)
    
    # Force flush all output
    sys.stdout.flush()
    sys.stderr.flush()
    
    print("\n" + "="*60)
    print("HARD SHUTDOWN: Terminating ASTRO process completely")
    print("="*60 + "\n")
    
    os._exit(0)  # Hard exit - no cleanup, no restart

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
