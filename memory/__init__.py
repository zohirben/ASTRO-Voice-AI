"""Memory Module for ASTRO Agent

Session-batched memory system using mem0 + ChromaDB for persistent context.

Architecture:
- **Startup**: Load past chat memories from mem0 (filtered by type="chat", user_id)
- **Session**: Buffer all user/assistant messages in memory (session_messages)
- **Shutdown**: Batch save all buffered messages to mem0 with session metadata

Future Extensions (TODO):
- Periodic auto-save for crash safety
- Document/RAG memory (type="doc")
- Streaming memory updates
- Cross-session memory search/retrieval
"""

from .manager import MemoryManager
from .config import MemoryConfig

__all__ = ["MemoryManager", "MemoryConfig"]
