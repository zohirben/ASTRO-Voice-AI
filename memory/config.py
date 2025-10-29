"""Memory Configuration for ASTRO Agent

Configuration for mem0 + ChromaDB integration with session-based metadata.
Uses Google Gemini for embeddings and LLM via google-genai package.

Requirements:
    - Environment variable: GOOGLE_API_KEY2_MEM0
    - Packages: mem0ai, google-genai, chromadb
    
Official Gemini support in mem0: https://docs.mem0.ai/components/llms/models/google_AI
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class MemoryConfig:
    """Configuration for memory system with Google Gemini.
    
    Uses Gemini for both LLM (memory extraction) and embeddings via google-genai package.
    Requires GOOGLE_API_KEY2_MEM0 in environment for authentication.
    
    Attributes:
        user_id: Unique identifier for user (filters memories)
        collection_name: ChromaDB collection name
        chroma_path: Local path for ChromaDB storage
        llm_provider: LLM provider (gemini)
        llm_model: LLM model (gemini-2.5-flash for memory extraction)
        llm_temperature: LLM temperature (0.0-1.0, default: 0.2 for consistency)
        llm_max_tokens: Maximum tokens for LLM output (default: 2000)
        embedder_provider: Embedder provider (gemini)
        embedder_model: Embedding model (models/text-embedding-004, 1536 dimensions)
        embedding_model_dims: Embedding dimensions for ChromaDB (1536 for Gemini)
        max_memories_load: Maximum memories to load on startup (None = all)
        enable_memory: Enable/disable memory system (env: ENABLE_MEMORY)
    """
    
    user_id: str = "default_user"
    collection_name: str = "astro_memories"
    chroma_path: str = "./memory_db"
    
    # Google Gemini for LLM and embeddings
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.5-flash"  # or "gemini-2.0-flash-001"
    llm_temperature: float = 0.2  # Low temperature for consistent extraction
    llm_max_tokens: int = 2000  # Sufficient for memory extraction
    
    # Google Gemini embeddings
    embedder_provider: str = "gemini"
    embedder_model: str = "models/text-embedding-004"  # 1536 dimensions
    embedding_model_dims: int = 1536  # Required for ChromaDB
    
    # Token management - keep token limit for cost control
    max_tokens_per_flush: int = 8000  # Maximum tokens to send to Gemini per extraction
    
    # REMOVED: enable_aggressive_filtering - no filtering needed, mem0 LLM handles it
    # REMOVED: max_message_length - let mem0 see full context for better reasoning
    
    max_memories_load: Optional[int] = 10  # Limit memories loaded at startup (was None)
    enable_memory: bool = field(default_factory=lambda: os.getenv("ENABLE_MEMORY", "true").lower() == "true")
    
    def to_mem0_config(self) -> Dict[str, Any]:
        """Convert to mem0 configuration dict with Gemini provider.
        
        Uses Google Gemini for both LLM and embeddings via google-genai package.
        API key from .env: GOOGLE_API_KEY2_MEM0
        
        CRITICAL: ChromaDB config only accepts: path, host, port, client, collection_name
        DO NOT include embedding_model_dims or any extra fields (causes Pydantic ValidationError)
        
        Returns:
            Dict with embedder, vector_store, and llm configuration for mem0.Memory.from_config()
        """
        config = {
            "llm": {
                "provider": self.llm_provider,  # "gemini"
                "config": {
                    "model": self.llm_model,
                    "temperature": self.llm_temperature,
                    "max_tokens": self.llm_max_tokens,
                }
            },
            "embedder": {
                "provider": self.embedder_provider,  # "gemini"
                "config": {
                    "model": self.embedder_model
                }
            },
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": self.collection_name,
                    "path": self.chroma_path,
                    # ONLY path, host, port, client, collection_name allowed
                    # embedding_model_dims is NOT a valid field and causes runtime errors
                }
            },
            "version": "v1.1"  # mem0 v1.0.0+
        }
        return config
