"""Google API Key Rotator for mem0 Memory System

Automatic key rotation when quota is exhausted (429 errors).
Persists current key index across agent restarts.

Architecture:
- Load 5 API keys from environment (GOOGLE_API_MEMORY_KEY1 through KEY5)
- Track current active key index in persistent file (./memory_key_index.txt)
- On 429 error: auto-advance to next key and save index
- Cycle through all keys; raise error when all exhausted

Usage:
    rotator = KeyRotator()
    api_key = rotator.get_current_key()
    
    # On quota error:
    if "429" in error or "RESOURCE_EXHAUSTED" in error:
        rotator.advance_to_next_key()
        api_key = rotator.get_current_key()
"""

import os
import logging
from typing import List, Optional
from pathlib import Path


logger = logging.getLogger(__name__)


class KeyRotator:
    """Manages automatic rotation of Google API keys for mem0.
    
    Supports up to 5 keys with persistent index tracking.
    Automatically advances to next key on quota exhaustion.
    """
    
    INDEX_FILE = "./memory_key_index.txt"
    MAX_KEYS = 5
    
    def __init__(self):
        """Initialize key rotator and load keys from environment."""
        self.keys: List[str] = self._load_keys_from_env()
        self.current_index: int = self._load_current_index()
        
        if not self.keys:
            logger.error("❌ No API keys found in environment!")
            logger.error("   Expected: GOOGLE_API_MEMORY_KEY1, KEY2, KEY3, KEY4, KEY5")
            raise ValueError("No Google API keys configured for memory system")
        
        logger.info(f"🔑 Key rotator initialized: {len(self.keys)} keys available")
        logger.info(f"   Current key index: {self.current_index} (Key #{self.current_index + 1})")
    
    def _load_keys_from_env(self) -> List[str]:
        """Load all available API keys from environment.
        
        Looks for: GOOGLE_API_MEMORY_KEY1 through GOOGLE_API_MEMORY_KEY5
        
        Returns:
            List of API keys (non-empty strings only)
        """
        keys = []
        for i in range(1, self.MAX_KEYS + 1):
            key_name = f"GOOGLE_API_MEMORY_KEY{i}"
            key_value = os.getenv(key_name)
            
            if key_value and key_value.strip():
                keys.append(key_value.strip())
                logger.debug(f"   ✓ Loaded {key_name}")
            else:
                logger.debug(f"   ✗ {key_name} not found or empty")
        
        return keys
    
    def _load_current_index(self) -> int:
        """Load persisted key index from file.
        
        Returns:
            Integer index (0 to len(keys)-1). Defaults to 0 if file missing.
        """
        try:
            if Path(self.INDEX_FILE).exists():
                with open(self.INDEX_FILE, 'r') as f:
                    index = int(f.read().strip())
                    
                # Validate index is within range
                if 0 <= index < len(self.keys):
                    logger.debug(f"📂 Loaded key index from file: {index}")
                    return index
                else:
                    logger.warning(f"⚠️  Invalid index in file ({index}), resetting to 0")
                    return 0
            else:
                logger.debug(f"📂 No index file found, starting at key 0")
                return 0
                
        except Exception as e:
            logger.warning(f"⚠️  Error loading key index: {e}. Defaulting to 0")
            return 0
    
    def _save_current_index(self) -> None:
        """Persist current key index to file."""
        try:
            with open(self.INDEX_FILE, 'w') as f:
                f.write(str(self.current_index))
            logger.debug(f"💾 Saved key index: {self.current_index}")
        except Exception as e:
            logger.error(f"❌ Failed to save key index: {e}")
    
    def get_current_key(self) -> str:
        """Get the currently active API key.
        
        Returns:
            API key string for current index
            
        Raises:
            ValueError: If no keys are available
        """
        if not self.keys:
            raise ValueError("No API keys available")
        
        return self.keys[self.current_index]
    
    def get_current_key_index(self) -> int:
        """Get the current key index (0-based).
        
        Returns:
            Current index (0 to len(keys)-1)
        """
        return self.current_index
    
    def get_total_keys(self) -> int:
        """Get total number of available keys.
        
        Returns:
            Total key count
        """
        return len(self.keys)
    
    def advance_to_next_key(self) -> bool:
        """Advance to the next available key and persist index.
        
        Returns:
            True if advanced to new key, False if all keys exhausted
        """
        if not self.keys:
            logger.error("❌ No keys available to advance")
            return False
        
        old_index = self.current_index
        self.current_index = (self.current_index + 1) % len(self.keys)
        self._save_current_index()
        
        logger.warning(f"🔄 Advanced from key #{old_index + 1} to key #{self.current_index + 1}")
        
        # Check if we've cycled through all keys (back to start)
        if self.current_index == 0 and old_index == len(self.keys) - 1:
            logger.critical("🚨 ALL API KEYS HAVE BEEN CYCLED - QUOTA EXHAUSTED ACROSS ALL KEYS")
            return False
        
        return True
    
    def reset_to_first_key(self) -> None:
        """Reset to first key (useful for new quota period).
        
        Call this at the start of a new day/month when quotas reset.
        """
        self.current_index = 0
        self._save_current_index()
        logger.info("🔄 Reset to first key (Key #1)")
    
    def is_all_keys_exhausted(self, attempted_indices: set) -> bool:
        """Check if all keys have been attempted in current cycle.
        
        Args:
            attempted_indices: Set of key indices that returned 429
            
        Returns:
            True if all keys have been tried and failed
        """
        return len(attempted_indices) >= len(self.keys)
    
    def get_status_report(self) -> str:
        """Get human-readable status report.
        
        Returns:
            Multi-line status string
        """
        lines = [
            f"Key Rotator Status:",
            f"  Total keys: {len(self.keys)}",
            f"  Current key: #{self.current_index + 1} (index {self.current_index})",
            f"  Index file: {self.INDEX_FILE}",
        ]
        return "\n".join(lines)
