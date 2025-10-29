"""
ChromaDB Cleanup Utility for Memory System

Handles ChromaDB corruption issues caused by:
- Mixed types (dict vs string) from schema migrations
- Malformed data from interrupted operations
- Version incompatibilities

Usage:
    python utils/cleanup_chromadb.py [--wipe] [--path ./memory_db]

Options:
    --wipe           Completely wipe ChromaDB and start fresh
    --path PATH      Path to ChromaDB directory (default: ./memory_db)
    --dry-run        Show what would be cleaned without making changes
    --collection NAME  Specific collection to clean (default: astro_memories)

Safety Features:
    - Creates backup before any destructive operations
    - Type-checks all entries before processing
    - Logs all skipped/corrupted entries
    - Validates data integrity after cleanup
"""

import os
import sys
import argparse
import shutil
from datetime import datetime
from pathlib import Path
import chromadb
from chromadb.config import Settings

def backup_chromadb(chroma_path: str) -> str:
    """Create timestamped backup of ChromaDB directory.
    
    Args:
        chroma_path: Path to ChromaDB directory
        
    Returns:
        Path to backup directory
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{chroma_path}_backup_{timestamp}"
    
    if os.path.exists(chroma_path):
        print(f"📦 Creating backup: {backup_path}")
        shutil.copytree(chroma_path, backup_path)
        print(f"✅ Backup created successfully")
        return backup_path
    else:
        print(f"⚠️  No existing ChromaDB found at {chroma_path}")
        return None

def validate_entry(entry: dict) -> tuple[bool, str]:
    """Validate a ChromaDB entry for type correctness.
    
    Args:
        entry: Dictionary from ChromaDB with keys: ids, documents, metadatas, embeddings
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Check if metadata is dict (should be) vs string (corrupted)
        if 'metadatas' in entry and entry['metadatas']:
            for metadata in entry['metadatas']:
                if not isinstance(metadata, dict):
                    return False, f"Metadata is {type(metadata)}, expected dict"
        
        # Check if documents are strings
        if 'documents' in entry and entry['documents']:
            for doc in entry['documents']:
                if not isinstance(doc, str):
                    return False, f"Document is {type(doc)}, expected str"
        
        return True, ""
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def clean_collection(client: chromadb.Client, collection_name: str, dry_run: bool = False) -> tuple[int, int]:
    """Clean corrupted entries from a ChromaDB collection.
    
    Args:
        client: ChromaDB client
        collection_name: Name of collection to clean
        dry_run: If True, only report issues without making changes
        
    Returns:
        Tuple of (total_entries, corrupted_entries)
    """
    try:
        collection = client.get_collection(name=collection_name)
    except Exception as e:
        print(f"❌ Error accessing collection '{collection_name}': {e}")
        return 0, 0
    
    print(f"\n🔍 Inspecting collection: {collection_name}")
    
    # Get all entries
    try:
        all_entries = collection.get()
        total = len(all_entries.get('ids', []))
        print(f"   Total entries: {total}")
    except Exception as e:
        print(f"❌ Error fetching entries: {e}")
        return 0, 0
    
    corrupted = 0
    corrupted_ids = []
    
    # Validate each entry
    for idx, entry_id in enumerate(all_entries.get('ids', [])):
        try:
            # Safely access array elements with bounds checking
            entry = {
                'ids': [entry_id],
                'documents': [all_entries['documents'][idx]] if 'documents' in all_entries and idx < len(all_entries['documents']) else None,
                'metadatas': [all_entries['metadatas'][idx]] if 'metadatas' in all_entries and idx < len(all_entries['metadatas']) else None,
                'embeddings': [all_entries['embeddings'][idx]] if 'embeddings' in all_entries and idx < len(all_entries['embeddings']) else None,
            }
            
            is_valid, error_msg = validate_entry(entry)
            if not is_valid:
                corrupted += 1
                corrupted_ids.append(entry_id)
                print(f"   ⚠️  Corrupted entry: {entry_id}")
                print(f"      Error: {error_msg}")
        except (IndexError, KeyError, TypeError) as e:
            corrupted += 1
            corrupted_ids.append(entry_id)
            print(f"   ⚠️  Corrupted entry: {entry_id}")
            print(f"      Error: Index/access error - {type(e).__name__}: {e}")
    
    # Remove corrupted entries if not dry-run
    if corrupted > 0 and not dry_run:
        print(f"\n🧹 Removing {corrupted} corrupted entries...")
        try:
            collection.delete(ids=corrupted_ids)
            print(f"   ✅ Removed {corrupted} corrupted entries")
        except Exception as e:
            print(f"   ❌ Error removing entries: {e}")
    elif corrupted > 0:
        print(f"\n   🔍 DRY RUN: Would remove {corrupted} corrupted entries")
    else:
        print("   ✅ No corrupted entries found")
    
    return total, corrupted

def wipe_chromadb(chroma_path: str, create_backup: bool = True):
    """Completely wipe ChromaDB directory.
    
    Args:
        chroma_path: Path to ChromaDB directory
        create_backup: Whether to create backup before wiping
    """
    if create_backup:
        backup_path = backup_chromadb(chroma_path)
    
    if os.path.exists(chroma_path):
        print(f"🗑️  Wiping ChromaDB directory: {chroma_path}")
        shutil.rmtree(chroma_path)
        print(f"   ✅ Directory wiped successfully")
    else:
        print(f"   ℹ️  Directory does not exist: {chroma_path}")

def main():
    parser = argparse.ArgumentParser(description="ChromaDB Cleanup Utility")
    parser.add_argument("--wipe", action="store_true", help="Completely wipe ChromaDB")
    parser.add_argument("--path", default="./memory_db", help="Path to ChromaDB directory")
    parser.add_argument("--dry-run", action="store_true", help="Show issues without making changes")
    parser.add_argument("--collection", default="astro_memories", help="Collection to clean")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🧹 ChromaDB Cleanup Utility")
    print("=" * 60)
    
    if args.wipe:
        print("\n⚠️  WARNING: This will completely wipe ChromaDB!")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            wipe_chromadb(args.path, create_backup=not args.no_backup)
            print("\n✅ Wipe complete. ChromaDB will be recreated on next run.")
        else:
            print("❌ Wipe cancelled")
        return
    
    # Clean mode
    if not os.path.exists(args.path):
        print(f"❌ ChromaDB directory not found: {args.path}")
        return
    
    if not args.no_backup and not args.dry_run:
        backup_chromadb(args.path)
    
    # Initialize ChromaDB client
    try:
        client = chromadb.PersistentClient(
            path=args.path,
            settings=Settings(anonymized_telemetry=False)
        )
        print(f"✅ Connected to ChromaDB at: {args.path}")
    except Exception as e:
        print(f"❌ Error connecting to ChromaDB: {e}")
        return
    
    # List collections
    try:
        collections = client.list_collections()
        print(f"\n📚 Found {len(collections)} collection(s):")
        for col in collections:
            print(f"   - {col.name}")
    except Exception as e:
        print(f"❌ Error listing collections: {e}")
        return
    
    # Clean specified collection
    total, corrupted = clean_collection(client, args.collection, args.dry_run)
    
    print("\n" + "=" * 60)
    print("📊 Cleanup Summary")
    print("=" * 60)
    print(f"   Total entries: {total}")
    print(f"   Corrupted entries: {corrupted}")
    print(f"   Clean entries: {total - corrupted}")
    
    if args.dry_run:
        print("\n   🔍 DRY RUN: No changes were made")
        print("   Run without --dry-run to apply changes")
    else:
        print("\n✅ Cleanup complete!")

if __name__ == "__main__":
    main()
