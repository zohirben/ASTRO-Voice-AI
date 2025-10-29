#!/usr/bin/env python3
"""Memory Key Manager Utility

Manage Google API key rotation for mem0 memory system.

Commands:
    status      - Show current key status
    reset       - Reset to first key (useful for new quota period)
    advance     - Manually advance to next key
    test        - Test current key with simple API call
    process     - Process fallback memory files (when quota restored)

Usage:
    python tools/memory_key_manager.py status
    python tools/memory_key_manager.py reset
    python tools/memory_key_manager.py advance
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory.key_rotator import KeyRotator
from dotenv import load_dotenv


def print_banner(title: str):
    """Print formatted banner."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def cmd_status():
    """Show current key rotation status."""
    print_banner("Memory Key Rotation Status")
    
    try:
        rotator = KeyRotator()
        print(rotator.get_status_report())
        print("\nKey Status:")
        for i in range(rotator.get_total_keys()):
            marker = "◀ ACTIVE" if i == rotator.get_current_key_index() else ""
            print(f"  Key #{i + 1}: Configured {marker}")
        print()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def cmd_reset():
    """Reset to first key."""
    print_banner("Reset to First Key")
    
    try:
        rotator = KeyRotator()
        old_index = rotator.get_current_key_index()
        rotator.reset_to_first_key()
        print(f"✅ Reset from Key #{old_index + 1} to Key #1")
        print("\nUse this at the start of a new day/month when quotas reset.")
        print()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def cmd_advance():
    """Manually advance to next key."""
    print_banner("Advance to Next Key")
    
    try:
        rotator = KeyRotator()
        old_index = rotator.get_current_key_index()
        success = rotator.advance_to_next_key()
        new_index = rotator.get_current_key_index()
        
        if success:
            print(f"✅ Advanced from Key #{old_index + 1} to Key #{new_index + 1}")
        else:
            print(f"⚠️  Cycled through all keys (back to Key #{new_index + 1})")
            print("   All keys may be exhausted.")
        print()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def cmd_test():
    """Test current API key with simple call."""
    print_banner("Test Current API Key")
    
    try:
        rotator = KeyRotator()
        current_key = rotator.get_current_key()
        key_index = rotator.get_current_key_index()
        
        print(f"Testing Key #{key_index + 1}...")
        print(f"Key preview: {current_key[:20]}...{current_key[-8:]}")
        
        # Simple test: try to import google-genai and make minimal call
        try:
            import google.genai as genai
            
            client = genai.Client(api_key=current_key)
            
            # List models (minimal API call)
            models = list(client.models.list())
            print(f"✅ Key #{key_index + 1} is VALID")
            print(f"   Found {len(models)} available models")
            print()
        except Exception as api_error:
            if "429" in str(api_error) or "quota" in str(api_error).lower():
                print(f"⚠️  Key #{key_index + 1} QUOTA EXHAUSTED")
                print(f"   Error: {api_error}")
            else:
                print(f"❌ Key #{key_index + 1} ERROR")
                print(f"   Error: {api_error}")
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def cmd_process_fallback():
    """Process fallback memory files."""
    print_banner("Process Fallback Memory Files")
    
    fallback_dir = Path("./memory_fallback")
    
    if not fallback_dir.exists():
        print("ℹ️  No fallback directory found (./memory_fallback/)")
        print("   This is created when API quota is exhausted.")
        print()
        return
    
    json_files = list(fallback_dir.glob("session_*.json"))
    
    if not json_files:
        print("ℹ️  No fallback files to process")
        print()
        return
    
    print(f"Found {len(json_files)} fallback session files:")
    for file in json_files:
        print(f"  • {file.name}")
    
    print("\n⚠️  Processing fallback files requires:")
    print("   1. At least one API key with available quota")
    print("   2. Running the processing script (to be implemented)")
    print("\nFor now, these files are preserved for manual processing.")
    print()


def main():
    """Main CLI handler."""
    # Load environment
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("Memory Key Manager")
        print("\nUsage:")
        print("  python tools/memory_key_manager.py <command>")
        print("\nCommands:")
        print("  status    - Show current key rotation status")
        print("  reset     - Reset to first key (for new quota period)")
        print("  advance   - Manually advance to next key")
        print("  test      - Test current key with API call")
        print("  process   - Check fallback memory files")
        print()
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    commands = {
        'status': cmd_status,
        'reset': cmd_reset,
        'advance': cmd_advance,
        'test': cmd_test,
        'process': cmd_process_fallback,
    }
    
    if command not in commands:
        print(f"❌ Unknown command: {command}")
        print(f"   Available: {', '.join(commands.keys())}")
        sys.exit(1)
    
    commands[command]()


if __name__ == "__main__":
    main()
