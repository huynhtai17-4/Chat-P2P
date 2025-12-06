"""
Data migration utility to consolidate user data from multiple folders into one.

This script merges data from old folders (tai, tai1, ta@gmail.com, etc.)
into a single normalized folder based on username.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from app.user_manager import _normalize_username, UserManager, User

DATA_DIR = "data"


def load_json_safe(filepath: Path) -> Optional[Dict]:
    """Safely load JSON file, return None if error."""
    try:
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"  Warning: Failed to load {filepath}: {e}")
    return None


def merge_peers(source_peers: Dict, target_peers: Dict) -> Dict:
    """Merge two peer dictionaries, keeping the most recent data."""
    merged = target_peers.copy()
    for peer_id, peer_info in source_peers.items():
        if peer_id not in merged:
            merged[peer_id] = peer_info
        else:
            # Keep the one with more recent last_seen
            source_last_seen = peer_info.get("last_seen", 0)
            target_last_seen = merged[peer_id].get("last_seen", 0)
            if source_last_seen > target_last_seen:
                merged[peer_id] = peer_info
    return merged


def merge_messages(source_messages: List, target_messages: List) -> List:
    """Merge two message lists, removing duplicates by message_id."""
    message_ids = {msg.get("message_id") for msg in target_messages}
    merged = target_messages.copy()
    
    for msg in source_messages:
        msg_id = msg.get("message_id")
        if msg_id and msg_id not in message_ids:
            merged.append(msg)
            message_ids.add(msg_id)
    
    # Sort by timestamp
    merged.sort(key=lambda m: m.get("timestamp", 0))
    return merged


def migrate_user_data(username: str, user_manager: UserManager) -> bool:
    """
    Migrate all data for a user to their normalized folder.
    
    Args:
        username: The username to migrate
        user_manager: UserManager instance
        
    Returns:
        True if migration successful, False otherwise
    """
    user = user_manager.get_user(username)
    if not user:
        print(f"  User {username} not found, skipping...")
        return False
    
    normalized_folder = user.get_folder_name()
    target_folder = Path(DATA_DIR) / normalized_folder
    target_folder.mkdir(parents=True, exist_ok=True)
    
    print(f"  Migrating data for {username} -> {normalized_folder}/")
    
    # Find all folders that might belong to this user
    potential_folders = []
    if os.path.isdir(DATA_DIR):
        for entry in os.listdir(DATA_DIR):
            folder_path = Path(DATA_DIR) / entry
            if not folder_path.is_dir():
                continue
            
            profile_path = folder_path / "profile.json"
            if profile_path.exists():
                profile_data = load_json_safe(profile_path)
                if profile_data:
                    profile_username = profile_data.get("username", "").lower()
                    if profile_username == username.lower():
                        potential_folders.append((entry, folder_path))
    
    if not potential_folders:
        print(f"    No source folders found for {username}")
        return False
    
    # Merge data from all source folders
    merged_peers = {}
    merged_messages = []
    merged_profile = user.to_dict()
    
    for folder_name, folder_path in potential_folders:
        if folder_name == normalized_folder:
            # Skip target folder itself
            continue
        
        print(f"    Merging from {folder_name}/")
        
        # Merge peers
        peers_path = folder_path / "peers.json"
        source_peers = load_json_safe(peers_path)
        if source_peers:
            merged_peers = merge_peers(source_peers, merged_peers)
        
        # Merge messages
        messages_path = folder_path / "messages.json"
        source_messages = load_json_safe(messages_path)
        if source_messages:
            merged_messages = merge_messages(source_messages, merged_messages)
        
        # Update profile with any missing fields
        profile_path = folder_path / "profile.json"
        source_profile = load_json_safe(profile_path)
        if source_profile:
            # Keep peer_id and tcp_port if they exist
            if "peer_id" in source_profile and "peer_id" not in merged_profile:
                merged_profile["peer_id"] = source_profile["peer_id"]
            if "tcp_port" in source_profile and "tcp_port" not in merged_profile:
                merged_profile["tcp_port"] = source_profile["tcp_port"]
    
    # Save merged data to target folder
    try:
        # Save profile
        profile_path = target_folder / "profile.json"
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(merged_profile, f, ensure_ascii=False, indent=2)
        print(f"    Saved profile.json")
        
        # Save peers
        if merged_peers:
            peers_path = target_folder / "peers.json"
            with open(peers_path, "w", encoding="utf-8") as f:
                json.dump(merged_peers, f, ensure_ascii=False, indent=2)
            print(f"    Saved peers.json ({len(merged_peers)} peers)")
        
        # Save messages
        if merged_messages:
            messages_path = target_folder / "messages.json"
            with open(messages_path, "w", encoding="utf-8") as f:
                json.dump(merged_messages, f, ensure_ascii=False, indent=2)
            print(f"    Saved messages.json ({len(merged_messages)} messages)")
        
        return True
    except Exception as e:
        print(f"    Error saving merged data: {e}")
        return False


def migrate_all_data():
    """
    Migrate all user data to normalized folders.
    This should be run once after updating the storage system.
    """
    print("=" * 60)
    print("Data Migration: Consolidating user folders")
    print("=" * 60)
    
    user_manager = UserManager()
    
    # Get all unique usernames
    usernames = set()
    if os.path.isdir(DATA_DIR):
        for entry in os.listdir(DATA_DIR):
            folder_path = Path(DATA_DIR) / entry
            if not folder_path.is_dir():
                continue
            
            profile_path = folder_path / "profile.json"
            if profile_path.exists():
                profile_data = load_json_safe(profile_path)
                if profile_data:
                    username = profile_data.get("username")
                    if username:
                        usernames.add(username)
    
    if not usernames:
        print("No users found to migrate.")
        return
    
    print(f"Found {len(usernames)} unique users to migrate:")
    print()
    
    success_count = 0
    for username in sorted(usernames):
        print(f"Migrating {username}...")
        if migrate_user_data(username, user_manager):
            success_count += 1
        print()
    
    print("=" * 60)
    print(f"Migration complete: {success_count}/{len(usernames)} users migrated")
    print("=" * 60)
    print()
    print("Note: Old folders are kept for safety.")
    print("You can manually delete them after verifying the migration.")


if __name__ == "__main__":
    migrate_all_data()

