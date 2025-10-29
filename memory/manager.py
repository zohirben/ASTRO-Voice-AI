"""Memory Manager for ASTRO Agent

Intelligent memory extraction architecture:
1. Startup: Load past meaningful memories (preferences, events, facts)
2. Session: Buffer user/assistant messages (but don't save everything)
3. Shutdown: Extract only meaningful information via mem0 intelligence

Key Design Principles:
- NOT a chat log dump—only save facts, preferences, events, tasks that matter
- Use mem0's extraction to classify and summarize into real memories
- Skip trivial queries ("What's the weather?") unless they reveal preferences
- Filter out injected system memory strings (don't re-save past context)
- Natural, human-like memory—not robotic fact listing
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

# mem0 v1.0.0+ uses 'mem0.memory.main' module structure
from mem0.memory.main import Memory

from .config import MemoryConfig
from .key_rotator import KeyRotator
# REMOVED: IntelligentMemoryUpdater, MemoryOperationExecutor - no longer needed
# mem0's Gemini LLM handles contradictions intelligently without hardcoded patterns


logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages intelligent memory extraction with mem0 + ChromaDB.
    
    Unlike raw chat storage, this system extracts ONLY meaningful information:
    - User preferences ("I like blue", "I prefer mornings")
    - Important events ("I have an interview", "My birthday is...")
    - Health/personal notes ("I'm allergic to...", "I work in...")
    - Open-ended tasks ("Remind me to...", "I might change jobs")
    - Significant history (context-rich facts, not trivial exchanges)
    
    Usage:
        # At agent startup
        manager = MemoryManager(config)
        await manager.initialize()
        past_context = manager.get_loaded_context()
        
        # During session - buffer messages
        manager.add_message(role="user", content="I have a job interview tomorrow")
        manager.add_message(role="assistant", content="Best of luck, sir!")
        
        # At shutdown - extract meaningful memories
        await manager.flush_session()
        await manager.close()
    """
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        """Initialize memory manager.
        
        Args:
            config: Memory configuration. If None, uses default MemoryConfig.
        """
        self.config = config or MemoryConfig()
        self.memory: Optional[Memory] = None
        self.key_rotator: Optional[KeyRotator] = None  # Key rotation manager
        self.session_id = str(uuid.uuid4())
        self.session_messages: List[Dict[str, str]] = []  # Buffer for current session
        self.loaded_memories: List[Dict[str, Any]] = []  # Meaningful memories from past
        self.session_start_time = datetime.now()  # Fixed: Use timezone-naive datetime
        self._initialized = False
        self._injected_memory_marker = "**Previous Conversation Context:**"  # To filter out
        
        logger.info(f"MemoryManager created with session_id={self.session_id}, user_id={self.config.user_id}")
    
    async def initialize(self) -> None:
        """Initialize mem0 and load past meaningful memories.
        
        This should be called once at agent startup before any session begins.
        Loads past memories filtered by user_id and type="memory" (not raw chat).
        """
        if not self.config.enable_memory:
            logger.warning("⚠️  MEMORY SYSTEM DISABLED (ENABLE_MEMORY=false in .env)")
            return
        
        try:
            logger.info(f"🔧 Initializing mem0 v1.0.0 with ChromaDB at {self.config.chroma_path}")
            logger.info(f"   • LLM: {self.config.llm_provider}/{self.config.llm_model}")
            logger.info(f"   • Embedder: {self.config.embedder_provider}/{self.config.embedder_model}")
            
            # Initialize key rotator for automatic API key management
            self.key_rotator = KeyRotator()
            logger.info(f"   • API Keys: {self.key_rotator.get_total_keys()} configured")
            
            # Set current API key in environment for mem0 to use
            current_key = self.key_rotator.get_current_key()
            os.environ["GOOGLE_API_KEY"] = current_key
            logger.info(f"   • Using Key #{self.key_rotator.get_current_key_index() + 1}")
            
            # Initialize mem0 with config
            mem0_config = self.config.to_mem0_config()
            self.memory = Memory.from_config(mem0_config)
            
            logger.info("✅ mem0 initialized successfully")
            
            # Load past meaningful memories (not raw chat logs)
            await self._load_past_memories()
            
            self._initialized = True
            logger.info(f"✅ MemoryManager initialized. Loaded {len(self.loaded_memories)} meaningful memories")
            
        except Exception as e:
            logger.error("=" * 60)
            logger.error("❌ CRITICAL: Failed to initialize memory system")
            logger.error("=" * 60)
            logger.error(f"Error: {type(e).__name__}: {e}")
            logger.error(f"Config: llm={self.config.llm_provider}, embedder={self.config.embedder_provider}")
            logger.error(f"DB Path: {self.config.chroma_path}")
            logger.error(f"ENABLE_MEMORY: {os.getenv('ENABLE_MEMORY', 'not set')}")
            logger.error("=" * 60)
            logger.error("🚨 MEMORY WILL BE DISABLED FOR THIS SESSION")
            logger.error("🚨 Check .env configuration and mem0ai version")
            logger.error("=" * 60)
            logger.error("Stack trace:", exc_info=True)
            # Don't fail agent startup if memory init fails
            self.config.enable_memory = False
    
    async def _load_past_memories(self) -> None:
        """Load past meaningful memories from mem0.
        
        Filters by:
        - user_id: self.config.user_id
        - metadata.type: "memory" (extracted facts, not raw chat)
        
        Respects config.max_memories_load for limiting results.
        
        Robust error handling: Skips any non-dict entries or corrupted DB rows.
        """
        if not self.memory:
            return
        
        try:
            logger.debug(f"Loading past memories for user_id={self.config.user_id}")
            
            # mem0 get_all() returns either:
            # - v1.0 API (mem0 <=0.x): direct list [mem1, mem2, mem3]
            # - v1.1+ API (mem0 1.x+): dict {"results": [mem1, mem2, mem3]}
            all_memories_raw = self.memory.get_all(user_id=self.config.user_id)
            
            # Handle both API formats
            if isinstance(all_memories_raw, dict) and "results" in all_memories_raw:
                # v1.1+ format: extract the list from the dict
                all_memories = all_memories_raw["results"]
                logger.debug(f"Using mem0 v1.1+ API format (dict with 'results' key)")
            elif isinstance(all_memories_raw, list):
                # v1.0 format: already a list
                all_memories = all_memories_raw
                logger.debug(f"Using mem0 v1.0 API format (direct list)")
            else:
                # Unexpected format
                logger.error(f"Unexpected get_all() return type: {type(all_memories_raw).__name__}")
                logger.error(f"Value: {all_memories_raw}")
                all_memories = []
            
            # Filter for type="memory" (extracted meaningful info)
            # Skip type="chat" (raw session dumps if any exist)
            # ROBUST: Skip any non-dict entries (strings, corrupted data from old schema)
            meaningful_memories = []
            skipped_count = 0
            
            for mem in all_memories:
                # CRITICAL FIX: Validate mem is a dict before calling .get()
                if not isinstance(mem, dict):
                    logger.warning(f"Skipping non-dict memory entry: {type(mem).__name__} - {str(mem)[:100]}")
                    skipped_count += 1
                    continue  # Skip this entry, continue to next
                
                # Safely extract metadata (default to empty dict)
                metadata = mem.get("metadata", {})
                
                # Validate metadata is also a dict
                if not isinstance(metadata, dict):
                    logger.warning(f"Skipping memory with non-dict metadata: {type(metadata).__name__}")
                    skipped_count += 1
                    continue  # Skip this entry, continue to next
                
                # Check memory type
                mem_type = metadata.get("type", "memory")  # Default to "memory" if not set
                
                # Accept "memory" type (extracted facts) or no type (legacy)
                # Reject "chat" type (raw logs)
                if mem_type != "chat":
                    meaningful_memories.append(mem)  # ✅ FIX: This line was always here, continue skips bad entries
            
            if skipped_count > 0:
                logger.warning(f"Skipped {skipped_count} corrupted/invalid memory entries (consider re-initializing ChromaDB)")
            
            # Apply max limit if configured
            if self.config.max_memories_load and len(meaningful_memories) > self.config.max_memories_load:
                # Take most recent memories (assuming they're sorted by creation time)
                meaningful_memories = meaningful_memories[-self.config.max_memories_load:]
                logger.info(f"Limited to {self.config.max_memories_load} most recent memories")
            
            self.loaded_memories = meaningful_memories
            logger.info(f"Loaded {len(meaningful_memories)} meaningful memories from mem0")
            
        except Exception as e:
            logger.error(f"Error loading past memories: {e}", exc_info=True)
            self.loaded_memories = []
    
    def get_loaded_context(self) -> str:
        """Get formatted string of past meaningful memories for agent context.
        
        Returns:
            Formatted string with past facts/preferences/events, suitable for agent prompt.
        """
        if not self.loaded_memories:
            return ""
        
        context_lines = ["**Past Memories:**"]
        for i, mem in enumerate(self.loaded_memories[-10:], 1):  # Last 10 memories
            memory_text = mem.get("memory", "")
            metadata = mem.get("metadata", {})
            
            # Include timestamp if available for temporal context
            created_at = metadata.get("created_at", "")
            if created_at:
                context_lines.append(f"{i}. [{created_at}] {memory_text}")
            else:
                context_lines.append(f"{i}. {memory_text}")
        
        return "\n".join(context_lines)
    
    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Estimate token count for messages (rough approximation).
        
        Uses 1 token ≈ 4 characters heuristic (conservative for English).
        Actual Gemini tokenization may vary, but this gives a safety estimate.
        
        Args:
            messages: List of message dicts with 'content' field
            
        Returns:
            Estimated token count
        """
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        estimated_tokens = total_chars // 4  # Conservative estimate (1 token ≈ 4 chars)
        return estimated_tokens
    
    # REMOVED: _should_buffer_message() - No filtering needed
    # mem0's Gemini LLM intelligently decides what's meaningful
    # Filtering was causing crashes and overriding LLM reasoning
    # Trust the AI - it's better at this than hardcoded patterns
    
    def add_message(self, role: str, content: str) -> None:
        """Buffer user/assistant messages for memory extraction.
        
        Simple Friday-style approach: Just buffer the conversation, let mem0's LLM decide what's meaningful.
        No filtering, no truncation - trust the LLM intelligence.
        
        Args:
            role: "user" or "assistant"
            content: Message text content
        """
        if not self.config.enable_memory:
            return
        
        # Only buffer actual conversation (not system/function messages)
        if role not in ["user", "assistant"]:
            logger.debug(f"Skipping non-user/assistant message: {role}")
            return
        
        # Simple append - no filtering, no truncation
        message = {"role": role, "content": content}
        self.session_messages.append(message)
        logger.debug(f"📝 Buffered: {role} - {len(content)} chars")
    
    async def flush_session(self) -> bool:
        """Extract and save meaningful memories with token limit enforcement.
        
        Returns:
            True if memories were successfully extracted and saved (or no messages to flush).
            False if flush failed (API error, quota exhausted, etc.).
        
        CRITICAL: This is NOT a chat log dump. mem0's intelligence extracts:
        - Preferences (likes, dislikes, habits)
        - Events (interviews, birthdays, appointments)
        - Personal facts (health, work, family)
        - Open-ended items (tasks, questions, pending topics)
        
        Random queries ("What's the weather?") are ignored unless they reveal preferences.
        
        Token Management:
        - Estimates token count before API call
        - Enforces max_tokens_per_flush limit (truncates oldest messages if needed)
        - Logs actual token usage for monitoring
        
        Metadata:
        {
            "type": "memory",  # Extracted facts, not raw chat
            "session_id": "<uuid>",
            "extracted_at": "<iso_timestamp>",
            "message_count": <int>,  # How many messages were analyzed
            "estimated_tokens": <int>  # Estimated tokens sent to Gemini
        }
        """
        if not self.config.enable_memory or not self.memory or not self.session_messages:
            logger.debug("No session messages to flush or memory disabled")
            return True  # Not an error - nothing to flush
        
        try:
            session_end_time = datetime.now()  # Fixed: Use timezone-naive datetime
            
            # Estimate tokens before API call
            estimated_tokens = self._estimate_tokens(self.session_messages)
            logger.info(f"📊 Extracting memories from {len(self.session_messages)} messages (~{estimated_tokens} tokens)")
            
            # Enforce token limit (safety check for API costs)
            max_tokens = self.config.max_tokens_per_flush
            if estimated_tokens > max_tokens:
                logger.warning(f"⚠️  Token count ({estimated_tokens}) exceeds limit ({max_tokens})")
                # Truncate to most recent messages (keep at least 5)
                while estimated_tokens > max_tokens and len(self.session_messages) > 5:
                    removed = self.session_messages.pop(0)  # Remove oldest
                    estimated_tokens = self._estimate_tokens(self.session_messages)
                    logger.debug(f"Removed oldest message, new token estimate: {estimated_tokens}")
                logger.warning(f"✂️  Truncated to {len(self.session_messages)} messages (~{estimated_tokens} tokens)")
            
            # Prepare metadata for extraction
            metadata = {
                "type": "memory",  # Extracted facts, NOT raw chat
                "session_id": self.session_id,
                "extracted_at": session_end_time.isoformat(),
                "message_count": len(self.session_messages),
                "estimated_tokens": estimated_tokens  # Track for monitoring
            }
            
            # mem0's add() will intelligently extract meaningful information
            # It won't save trivial exchanges or duplicate info
            # The LLM backend (Gemini) analyzes conversation for facts/preferences/events
            
            # Try extraction with automatic key rotation on quota errors
            result = await self._extract_with_key_rotation(metadata)
            
            # CRITICAL FIX: Detect when mem0 returns empty result due to Gemini API failure
            # mem0 logs "Invalid JSON response" error but returns {'results': []} instead of raising
            # This is a silent failure that loses user's memories
            if isinstance(result, dict) and result.get("results") is not None:
                # This is the v1.1+ format - check if results are empty
                extracted_list = result.get("results", [])
                if len(extracted_list) == 0 and len(self.session_messages) > 2:
                    # SUSPICIOUS: User had multiple messages but extraction returned nothing
                    # This likely means Gemini API failed silently
                    logger.warning("⚠️  EMPTY EXTRACTION DETECTED: Multiple messages but zero results")
                    logger.warning("   This may indicate a Gemini API failure (check logs for 'Invalid JSON response')")
                    logger.warning("   Attempting retry with next API key...")
                    
                    # Try once more with next key
                    self.key_rotator.advance_to_next_key()
                    new_key = self.key_rotator.get_current_key()
                    os.environ["GOOGLE_API_KEY"] = new_key
                    
                    retry_result = await self._extract_with_key_rotation(metadata)
                    if isinstance(retry_result, dict) and len(retry_result.get("results", [])) == 0:
                        logger.error("🚨 RETRY ALSO FAILED: Memories will be LOST!")
                        logger.error("   Check Gemini API status and key validity")
                        return False
                    else:
                        result = retry_result  # Use retry result
                        logger.info("✅ Retry succeeded!")
            
            # Log what was extracted (if any)
            if result:
                # Handle both v1.0 (list) and v1.1+ (dict) formats
                if isinstance(result, list):
                    extracted_count = len(result)
                elif isinstance(result, dict) and "results" in result:
                    extracted_count = len(result.get("results", []))
                else:
                    extracted_count = 1
                    
                logger.info(f"✅ Extracted {extracted_count} meaningful memories (used ~{estimated_tokens} tokens)")
                logger.debug(f"Extraction result: {result}")
            else:
                logger.info(f"ℹ️  No new memories extracted (trivial conversation, ~{estimated_tokens} tokens used)")
            
            # mem0's Gemini LLM handles contradictions naturally - no manual intervention needed
            # REMOVED: IntelligentUpdater - was overriding LLM reasoning with hardcoded patterns
            # Trust the AI - it's designed to detect contradictions and update intelligently
            
            # Clear session buffer
            self.session_messages.clear()
            
            # Generate new session_id for next session (if agent continues)
            self.session_id = str(uuid.uuid4())
            self.session_start_time = datetime.now()  # Fixed: Use timezone-naive datetime
            
            return True  # Success!
            
        except Exception as e:
            logger.error(f"❌ Error extracting memories from session: {e}", exc_info=True)
            
            # Fallback: Save raw messages to disk when API fails (429, network issues)
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower() or "exhausted" in error_str.lower():
                if "All" in error_str and "keys" in error_str:
                    logger.critical("🚨 ALL API KEYS EXHAUSTED - Cannot extract memories")
                    logger.critical(f"   Tried {self.key_rotator.get_total_keys() if self.key_rotator else 'N/A'} keys")
                    logger.critical("   ⚠️  Saving to fallback file for later processing")
                else:
                    logger.warning("⚠️  API quota error - saving raw messages to disk for later processing")
                self._save_raw_to_disk()
            else:
                logger.error("🚨 Non-quota error - messages will be lost!")
            
            # Don't pretend it succeeded
            return False
    
    async def _extract_with_key_rotation(self, metadata: Dict[str, Any]) -> Any:
        """Extract memories with automatic key rotation on quota errors.
        
        Tries current key, advances to next on 429 errors.
        Cycles through all available keys before giving up.
        
        Args:
            metadata: Session metadata for extraction
            
        Returns:
            Extraction result from mem0.add() or None on failure
            
        Raises:
            Exception: If all keys exhausted or non-quota error occurs
        """
        if not self.key_rotator:
            # No key rotator (shouldn't happen, but fallback to direct call)
            logger.warning("⚠️  Key rotator not initialized, attempting direct extraction")
            return self.memory.add(
                self.session_messages,
                user_id=self.config.user_id,
                metadata=metadata
            )
        
        attempted_keys = set()
        max_attempts = self.key_rotator.get_total_keys()
        
        for attempt in range(max_attempts):
            current_index = self.key_rotator.get_current_key_index()
            
            # Skip if we already tried this key
            if current_index in attempted_keys:
                logger.warning(f"⚠️  Already tried key #{current_index + 1}, advancing...")
                self.key_rotator.advance_to_next_key()
                continue
            
            attempted_keys.add(current_index)
            
            try:
                logger.debug(f"🔑 Attempting extraction with Key #{current_index + 1}")
                
                # mem0 uses the API key from environment (set during init)
                result = self.memory.add(
                    self.session_messages,
                    user_id=self.config.user_id,
                    metadata=metadata
                )
                
                logger.info(f"✅ Extraction successful with Key #{current_index + 1}")
                return result
                
            except Exception as e:
                error_str = str(e)
                
                # Check if this is a quota error
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                    logger.warning(f"⚠️  Key #{current_index + 1} quota exhausted: {e}")
                    
                    # Try to advance to next key
                    if attempt < max_attempts - 1:
                        advanced = self.key_rotator.advance_to_next_key()
                        if advanced:
                            # Update environment for mem0
                            new_key = self.key_rotator.get_current_key()
                            os.environ["GOOGLE_API_KEY"] = new_key
                            
                            # Reinitialize mem0 with new key
                            logger.info(f"🔄 Reinitializing mem0 with Key #{self.key_rotator.get_current_key_index() + 1}")
                            mem0_config = self.config.to_mem0_config()
                            self.memory = Memory.from_config(mem0_config)
                            
                            continue  # Retry with new key
                        else:
                            logger.critical("🚨 All API keys exhausted - cannot rotate further")
                            raise Exception("All Google API keys have reached quota limit")
                    else:
                        logger.critical("🚨 Tried all available keys - quota exhausted across all keys")
                        raise Exception(f"All {max_attempts} API keys exhausted")
                else:
                    # Non-quota error - don't retry with other keys
                    logger.error(f"❌ Non-quota error with Key #{current_index + 1}: {e}")
                    raise  # Re-raise non-quota errors immediately
        
        # Should never reach here, but just in case
        raise Exception("Memory extraction failed after trying all available keys")
    
    def _save_raw_to_disk(self) -> None:
        """Save raw session messages to disk when API fails (fallback).
        
        Creates a JSON file in ./memory_fallback/ with session messages.
        These can be processed later when API quota is restored.
        """
        import json
        import os
        
        fallback_dir = "./memory_fallback"
        os.makedirs(fallback_dir, exist_ok=True)
        
        filename = f"{fallback_dir}/session_{self.session_id}.json"
        
        try:
            data = {
                "session_id": self.session_id,
                "user_id": self.config.user_id,
                "timestamp": datetime.now().isoformat(),
                "messages": self.session_messages,
                "message_count": len(self.session_messages),
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Saved {len(self.session_messages)} messages to {filename}")
        except Exception as e:
            logger.error(f"Failed to save fallback file: {e}")
    
    async def periodic_save(self, interval_seconds: int = 300) -> None:
        """Periodic auto-save (optional, for crash safety).
        
        TODO: Implement this for production use cases requiring crash resilience.
        Should run in background task, saving session every N seconds.
        
        Args:
            interval_seconds: Save interval in seconds (default: 5 minutes)
        """
        # Future implementation for auto-save
        # while True:
        #     await asyncio.sleep(interval_seconds)
        #     if self.session_messages:
        #         await self.flush_session()
        pass
    
    async def close(self) -> None:
        """Close memory manager and clean up resources.
        
        Should be called at agent shutdown after flush_session().
        """
        if self.memory:
            logger.info("Closing memory manager")
            # mem0 v0.x doesn't require explicit close, but we'll clear references
            self.memory = None
        
        self._initialized = False
    
    # ============================================================================
    # Future Extensions (Placeholders)
    # ============================================================================
    
    def search_memories(self, query: str, memory_type: str = "chat", limit: int = 5) -> List[Dict[str, Any]]:
        """Search past memories by semantic query.
        
        TODO: Implement for RAG and context retrieval.
        
        Args:
            query: Natural language search query
            memory_type: Filter by memory type ("chat", "doc", etc.)
            limit: Maximum results to return
            
        Returns:
            List of relevant memories with scores
        """
        if not self.memory:
            return []
        
        try:
            # mem0 v0.x search
            results = self.memory.search(query, user_id=self.config.user_id, limit=limit)
            
            # Filter by memory_type in metadata
            filtered_results = []
            for result in results:
                metadata = result.get("metadata", {})
                if isinstance(metadata, dict) and metadata.get("type") == memory_type:
                    filtered_results.append(result)
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error searching memories: {e}", exc_info=True)
            return []
    
    async def add_document_memory(self, content: str, metadata: Dict[str, Any]) -> None:
        """Add document/RAG memory (type="doc").
        
        TODO: Implement for PDF/doc ingestion and RAG.
        
        Args:
            content: Document content or summary
            metadata: Should include {"type": "doc", "source": "filename.pdf", ...}
        """
        if not self.memory:
            return
        
        try:
            # Ensure type="doc" in metadata
            metadata["type"] = "doc"
            
            result = self.memory.add(
                content,
                user_id=self.config.user_id,
                metadata=metadata
            )
            
            logger.info(f"Document memory added: {result}")
            
        except Exception as e:
            logger.error(f"Error adding document memory: {e}", exc_info=True)
    
    # REMOVED: _execute_intelligent_memory_updates() - 80 LOC of overengineering
    # mem0's Gemini LLM is designed to handle contradictions intelligently
    # We were applying dumb regex patterns AFTER smart LLM reasoning
    # Trust the AI - let it do what it's designed for

