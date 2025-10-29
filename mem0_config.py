"""
Standalone mem0 Configuration Example - Gemini-Only Stack

This file demonstrates the minimal configuration needed for mem0 with:
- Google Gemini for LLM (memory extraction)
- Google Gemini for embeddings
- ChromaDB for vector storage with on-disk persistence

Usage:
    from mem0 import Memory
    from mem0_config import CONFIG
    
    memory = Memory.from_config(CONFIG)

Requirements:
    - Environment variable: GOOGLE_API_KEY2_MEM0
    - Environment variable: CHROMA_PATH (optional, defaults to ./memory_db)
    - Packages: mem0ai, google-genai, chromadb, python-dotenv
"""

import os

CONFIG = {
    "llm": {
        "provider": "gemini",
        "config": {
            "model": "gemini-2.5-flash",           # or "gemini-2.0-flash-001" as needed
            "temperature": 0.2,                    # Low for consistent memory extraction
            "max_tokens": 2000,                    # Sufficient for memory processing
        },
    },
    "embedder": {
        "provider": "gemini",
        "config": {
            "model": "models/text-embedding-004",  # 1536 dims (standard Gemini embedder)
        },
    },
    "vector_store": {
        "provider": "chroma",                      # ChromaDB for local vector storage
        "config": {
            "collection_name": "mem0",             # Collection name in ChromaDB
            "path": os.getenv("CHROMA_PATH", "./memory_db"),  # Local persistence path
            # ONLY these fields allowed: path, host, port, client, collection_name
            # DO NOT add embedding_model_dims or any extras (causes ValidationError)
        },
    },
    "version": "v1.1",  # mem0 configuration version
}
