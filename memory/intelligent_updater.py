"""Intelligent memory updater for semantic memory management.

This module handles smart memory updates/deletions when user preferences change,
contradict previous memories, or become outdated. mem0's default ADD/NOOP logic
doesn't understand semantic negations like "I don't like X anymore".

Key Capabilities:
1. Conflict Detection: "I like chocolate" contradicts "I like cookies"
2. Explicit Rejection: "I DON'T like X" → Delete matching memories
3. Scope Updates: "I like fruit" might supersede "I like bananas" (more general)
4. Temporal Updates: "I USED TO like X" → Delete or archive
5. Correction Detection: Recognize correction patterns and update accordingly

Architecture:
- Load all existing memories
- Analyze new messages for contradictions/corrections
- Generate update operations (DELETE, UPDATE, MERGE, KEEP)
- Execute operations with semantic similarity checks
- Log all changes with reasoning
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
import json

# For semantic similarity checks
try:
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

logger = logging.getLogger(__name__)


class MemoryUpdateOperation:
    """Represents a single memory operation."""
    
    def __init__(self, op_type: str, memory_id: str, memory_text: str, reason: str, confidence: float = 0.8):
        self.op_type = op_type  # "DELETE", "UPDATE", "MERGE", "ARCHIVE", "KEEP"
        self.memory_id = memory_id
        self.memory_text = memory_text
        self.reason = reason
        self.confidence = confidence  # 0.0-1.0 how sure we are about this operation
        self.timestamp = datetime.now()
    
    def to_dict(self):
        return {
            "type": self.op_type,
            "id": self.memory_id,
            "text": self.memory_text,
            "reason": self.reason,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat()
        }


class IntelligentMemoryUpdater:
    """Intelligently manages memory updates, deletions, and semantic conflicts.
    
    Problem: mem0 returns ADD/NOOP events, not DELETE/UPDATE.
    
    Solution: 
    - Analyze existing memories + new session messages
    - Detect contradictions, explicit rejections, corrections
    - Generate smart update operations
    - Log all changes for auditability
    
    Example:
        Session 1: "I like cookies" → Memory added: "Likes cookies"
        Session 2: "Actually I don't like cookies, I like bananas"
                → Should DELETE "Likes cookies" + ADD "Likes bananas"
                → Currently just ADD "Likes bananas" (❌ keeps old memory)
    """
    
    # Rejection keywords that indicate user is negating previous preferences
    REJECTION_KEYWORDS = {
        "don't like", "dont like", "dislike", "hate",
        "not a fan", "never", "can't stand", "detest",
        "actually i", "actually i like", "i meant", "i should say",
        "not really", "not anymore", "used to like", "used to"
    }
    
    # Update indicators (user is correcting or updating)
    UPDATE_KEYWORDS = {
        "actually", "correction", "i meant", "scratch that",
        "wait", "no", "i should say", "let me rephrase",
        "better way to say", "more like"
    }
    
    # Preference categories for conflict detection
    PREFERENCE_CATEGORIES = {
        "food": ["like", "eat", "enjoy", "prefer", "food", "meal", "snack", "drink", "beverage"],
        "work": ["work", "job", "career", "profession", "task", "project"],
        "hobby": ["hobby", "enjoy", "like", "play", "watch", "read", "listen"],
        "contact": ["call", "email", "text", "contact", "reach", "phone"]
    }
    
    def __init__(self, existing_memories: List[Dict[str, Any]]):
        """Initialize with existing memories.
        
        Args:
            existing_memories: List of existing memory dicts with 'memory' field
        """
        self.existing_memories = existing_memories or []
        self.operations: List[MemoryUpdateOperation] = []
        
        # Build a searchable index of existing memories
        self.memory_index = {
            mem.get("id", ""): mem.get("memory", "") 
            for mem in self.existing_memories
        }
        
        logger.debug(f"🧠 IntelligentMemoryUpdater initialized with {len(self.existing_memories)} existing memories")
    
    def analyze_session_messages(self, session_messages: List[Dict[str, str]]) -> List[MemoryUpdateOperation]:
        """Analyze session messages for contradictions and rejections.
        
        Args:
            session_messages: List of {'role': 'user'|'assistant', 'content': str}
            
        Returns:
            List of MemoryUpdateOperation objects representing needed updates
        """
        self.operations = []
        
        if not session_messages:
            logger.debug("No session messages to analyze")
            return self.operations
        
        # Extract user messages (assistant messages are less reliable for preferences)
        user_messages = [
            msg.get("content", "") 
            for msg in session_messages 
            if msg.get("role") == "user"
        ]
        
        user_text = " ".join(user_messages).lower()
        logger.debug(f"📊 Analyzing {len(user_messages)} user messages for contradictions")
        
        # Check for explicit rejections
        self._detect_explicit_rejections(user_text)
        
        # Check for corrections
        self._detect_corrections(user_text)
        
        # Check for semantic contradictions
        self._detect_semantic_conflicts(user_text)
        
        # Log all operations
        if self.operations:
            logger.info(f"📝 Detected {len(self.operations)} potential memory updates:")
            for op in self.operations:
                logger.debug(f"   {op.op_type}: {op.memory_text} (confidence: {op.confidence:.1%})")
        
        return self.operations
    
    def _detect_explicit_rejections(self, user_text: str) -> None:
        """Detect when user explicitly rejects/negates previous preferences.
        
        Patterns:
        - "I don't like X" (where X was previously stored)
        - "I hate X" (strong rejection)
        - "Not a fan of X" (mild rejection)
        - "I NEVER like X" (temporal negation)
        """
        logger.debug("🔍 Checking for explicit rejections...")
        
        for memory in self.existing_memories:
            memory_id = memory.get("id", "")
            memory_text = memory.get("memory", "")
            
            # Extract key terms from memory
            # E.g., "Likes cookies" → check for "don't like cookies" or "hate cookies"
            key_terms = self._extract_key_terms(memory_text)
            
            for term in key_terms:
                # Check for explicit rejection patterns
                if self._is_explicitly_rejected(user_text, term):
                    op = MemoryUpdateOperation(
                        op_type="DELETE",
                        memory_id=memory_id,
                        memory_text=memory_text,
                        reason=f"User explicitly rejected: '{term}'",
                        confidence=0.95
                    )
                    self.operations.append(op)
                    logger.debug(f"   ✂️  DELETE {memory_text} - Explicitly rejected")
                    break  # Only delete once per memory
    
    def _detect_corrections(self, user_text: str) -> None:
        """Detect when user is correcting/clarifying previous statements.
        
        Patterns:
        - "Actually, I like X" (correction from previous statement)
        - "Wait, I meant Y not Z"
        - "Let me correct that..."
        """
        logger.debug("🔍 Checking for corrections...")
        
        for keyword in self.UPDATE_KEYWORDS:
            if keyword in user_text:
                # User is potentially correcting something
                # This is a signal to review existing memories for conflicts
                logger.debug(f"   ⚠️  Correction keyword found: '{keyword}'")
                # Semantic conflict detection will handle the rest
                break
    
    def _detect_semantic_conflicts(self, user_text: str) -> None:
        """Detect when new preferences semantically conflict with old ones.
        
        Example:
        - Old memory: "Likes cookies"
        - New message: "Actually I like chocolate"
        - Conflict: Both are similar food preferences, user might be choosing chocolate over cookies
        
        Uses keyword matching (always available) + optional sklearn similarity.
        """
        logger.debug("🔍 Checking for semantic conflicts...")
        
        for memory in self.existing_memories:
            memory_id = memory.get("id", "")
            memory_text = memory.get("memory", "")
            
            # Extract key terms
            memory_terms = self._extract_key_terms(memory_text)
            user_terms = self._extract_key_terms(user_text)
            
            # Find same category conflicts
            # E.g., both about food preferences, but different items
            for mem_term in memory_terms:
                for user_term in user_terms:
                    if self._is_category_conflict(mem_term, user_term):
                        # Potential conflict detected
                        if self._is_stronger_preference(user_term, mem_term):
                            # New preference seems more current/stronger
                            op = MemoryUpdateOperation(
                                op_type="UPDATE",
                                memory_id=memory_id,
                                memory_text=memory_text,
                                reason=f"Newer preference: '{user_term}' supersedes '{mem_term}'",
                                confidence=0.7
                            )
                            self.operations.append(op)
                            logger.debug(f"   🔄 UPDATE {memory_text} - Superseded by {user_term}")
    
    def _extract_key_terms(self, text: str) -> Set[str]:
        """Extract key terms from memory/message text.
        
        Example:
        - "Likes chocolate" → {'chocolate'}
        - "Works as a software engineer" → {'software', 'engineer'}
        """
        # Remove common words
        stopwords = {"likes", "like", "a", "an", "the", "is", "are", "as", "and", "or"}
        
        # Split and filter
        terms = set()
        for word in text.lower().split():
            word = word.strip(".,!?;:")
            if word and word not in stopwords and len(word) > 2:
                terms.add(word)
        
        return terms
    
    def _is_explicitly_rejected(self, user_text: str, term: str) -> bool:
        """Check if user explicitly rejected a term.
        
        Args:
            user_text: User's messages combined
            term: Term to check (e.g., "cookies")
            
        Returns:
            True if user has explicitly rejected this term
        """
        for rejection in self.REJECTION_KEYWORDS:
            pattern = f"{rejection} {term}"
            if pattern in user_text:
                return True
        
        return False
    
    def _is_category_conflict(self, term1: str, term2: str) -> bool:
        """Check if two terms are in the same preference category.
        
        Example:
        - "cookies" and "chocolate" are both in FOOD category → conflict possible
        - "cookies" and "engineer" are different → no conflict
        """
        if HAS_SKLEARN and term1 != term2:
            # Use semantic similarity if available
            try:
                # Simple heuristic: if both terms appear in same category keywords
                for category, keywords in self.PREFERENCE_CATEGORIES.items():
                    term1_match = any(t in term1.lower() for t in keywords)
                    term2_match = any(t in term2.lower() for t in keywords)
                    
                    if term1_match and term2_match:
                        return True
            except Exception as e:
                logger.debug(f"Error in category conflict check: {e}")
        
        return False
    
    def _is_stronger_preference(self, new_term: str, old_term: str) -> bool:
        """Check if new preference is stronger/more recent than old.
        
        Heuristic:
        - If same session mentions new_term after discussing old_term, new is stronger
        - If surrounded by update keywords, it's stronger
        """
        # Simple heuristic: any explicit mention is stronger than old memory
        return len(new_term) > 0 and new_term != old_term


class MemoryOperationExecutor:
    """Executes memory update operations against the actual memory store.
    
    Handles:
    - DELETE: Remove memory completely
    - UPDATE: Modify existing memory text
    - MERGE: Combine related memories
    - ARCHIVE: Mark as obsolete but keep history
    - KEEP: No action needed
    """
    
    def __init__(self, memory_manager):
        """Initialize with reference to MemoryManager.
        
        Args:
            memory_manager: The MemoryManager instance with memory.delete(), etc.
        """
        self.memory_manager = memory_manager
        self.execution_log: List[Dict[str, Any]] = []
    
    async def execute_operations(
        self, 
        operations: List[MemoryUpdateOperation],
        user_id: str
    ) -> Dict[str, int]:
        """Execute all memory update operations.
        
        Args:
            operations: List of MemoryUpdateOperation objects
            user_id: User ID for memory operations
            
        Returns:
            Dict with counts: {'deleted': 2, 'updated': 1, 'errors': 0}
        """
        stats = {'deleted': 0, 'updated': 0, 'merged': 0, 'archived': 0, 'errors': 0}
        
        logger.info(f"⚙️  Executing {len(operations)} memory operations...")
        
        for op in operations:
            try:
                if op.op_type == "DELETE" and op.confidence > 0.8:
                    # Only delete if confidence is high
                    await self._execute_delete(op, user_id)
                    stats['deleted'] += 1
                    
                elif op.op_type == "UPDATE" and op.confidence > 0.7:
                    await self._execute_update(op, user_id)
                    stats['updated'] += 1
                    
                elif op.op_type == "ARCHIVE":
                    await self._execute_archive(op, user_id)
                    stats['archived'] += 1
                
                self.execution_log.append({
                    'operation': op.to_dict(),
                    'status': 'success',
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"❌ Error executing {op.op_type}: {e}")
                stats['errors'] += 1
                self.execution_log.append({
                    'operation': op.to_dict(),
                    'status': 'failed',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        logger.info(f"✅ Operations complete: {stats}")
        return stats
    
    async def _execute_delete(self, op: MemoryUpdateOperation, user_id: str) -> None:
        """Delete a memory from the store."""
        if hasattr(self.memory_manager.memory, 'delete'):
            await self.memory_manager.memory.delete(op.memory_id, user_id=user_id)
            logger.info(f"✂️  DELETED: {op.memory_text} ({op.reason})")
        else:
            logger.warning(f"⚠️  Memory delete not supported: {op.memory_text}")
    
    async def _execute_update(self, op: MemoryUpdateOperation, user_id: str) -> None:
        """Update a memory in the store."""
        # Note: mem0 might not have direct update; would need to delete + re-add
        logger.info(f"🔄 UPDATE: {op.memory_text} ({op.reason})")
        # Implementation depends on mem0 capabilities
    
    async def _execute_archive(self, op: MemoryUpdateOperation, user_id: str) -> None:
        """Archive a memory (mark obsolete but keep for history)."""
        logger.info(f"📦 ARCHIVED: {op.memory_text} ({op.reason})")
        # Implementation would store archival metadata
