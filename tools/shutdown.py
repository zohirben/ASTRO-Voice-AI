"""Shutdown Tool for ASTRO Agent

Provides voice/CLI-triggered agent shutdown with proper memory flush and hard process termination.

Usage via voice:
  User: "Shutdown yourself ASTRO"
  User: "End session"
  User: "Turn off"
  
CRITICAL: Uses os._exit(0) for true hard shutdown—no respawn, no restart, complete process termination.
This ensures clean shutdown for future web UI integration where orchestrator controls restarts.
"""

import os
import logging
from livekit.agents import function_tool, RunContext

logger = logging.getLogger(__name__)


# Global reference to memory manager (set by agent.py)
_memory_manager = None


def set_memory_manager(manager):
    """Set global memory manager reference.
    
    Called by agent.py during startup to register the memory manager.
    """
    global _memory_manager
    _memory_manager = manager


@function_tool
async def shutdown_agent(context: RunContext) -> str:
    """Shutdown the agent and fully terminate the current Python process.
    
    This tool triggers a HARD shutdown (not just session disconnect):
    1. Flushes current session memory to storage
    2. Closes memory manager cleanly
    3. Returns goodbye message for agent to speak
    4. Process termination handled by agent.py after goodbye
    
    Use when user explicitly requests to end the session:
    - "Shutdown yourself ASTRO"
    - "End the session"
    - "Turn off"
    - "Goodbye"
    
    Why os._exit(0)?
    - No respawn/auto-restart behavior
    - Complete process termination
    - Clean for web UI integration—orchestrator (UI/cloud/shell) decides when to restart
    - No lingering threads or cleanup handlers that might restart session
    
    Returns:
        Confirmation message for voice output (agent will speak this before exit)
    """
    try:
        logger.critical("🛑 USER REQUESTED SHUTDOWN - INITIATING TERMINATION SEQUENCE")
        
        # Step 1: Flush session memory
        if _memory_manager and _memory_manager.config.enable_memory:
            logger.info("💾 Flushing session memory before shutdown...")
            flush_success = await _memory_manager.flush_session()
            if flush_success:
                logger.info("✅ Memory flushed successfully")
            else:
                logger.warning("⚠️  Memory flush failed - check logs above for details")
            
            await _memory_manager.close()
            logger.info("✅ Memory manager closed")
        else:
            logger.info("⚠️  Memory system disabled - skipping flush")
        
        # Step 2: Return message for agent to speak
        # The calling code in agent.py will handle os._exit(0) after this returns
        return "Shutting down now. Goodbye, sir. It has been a pleasure serving you."
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}", exc_info=True)
        return f"error: shutdown encountered an issue: {str(e)}"


async def execute_hard_shutdown():
    """Execute hard shutdown after agent speaks goodbye message.
    
    Call this AFTER the agent has spoken the shutdown message.
    This ensures the user hears the goodbye before process terminates.
    """
    logger.info("Executing hard shutdown with os._exit(0)")
    os._exit(0)  # Hard exit - no cleanup, no restart, complete termination
