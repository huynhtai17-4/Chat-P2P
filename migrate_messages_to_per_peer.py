import json
import os
import shutil
from pathlib import Path
from typing import Dict, List

def migrate_user_data(username: str):
    print(f"\n=== Migrating data for user: {username} ===")
    
    user_dir = Path("data") / username
    if not user_dir.exists():
        print(f"User directory not found: {user_dir}")
        return
    
    messages_file = user_dir / "messages.json"
    if not messages_file.exists():
        print(f"No messages.json found for {username}, skipping migration")
        return
    
    print(f"Reading {messages_file}...")
    try:
        with open(messages_file, 'r', encoding='utf-8') as f:
            all_messages = json.load(f)
    except Exception as e:
        print(f"Error reading messages.json: {e}")
        return
    
    if not all_messages:
        print("No messages to migrate")
        return
    
    print(f"Found {len(all_messages)} total messages")
    
    backup_file = user_dir / "messages.json.backup"
    if not backup_file.exists():
        print(f"Creating backup: {backup_file}")
        shutil.copy(messages_file, backup_file)
    
    grouped_by_peer: Dict[str, List[dict]] = {}
    
    peers_file = user_dir / "peers.json"
    peer_id_map: Dict[str, str] = {}
    
    if peers_file.exists():
        try:
            with open(peers_file, 'r', encoding='utf-8') as f:
                peers_data = json.load(f)
                for peer_id in peers_data.keys():
                    peer_id_map[peer_id] = peer_id
        except Exception as e:
            print(f"Warning: Could not read peers.json: {e}")
    
    profile_file = user_dir / "profile.json"
    my_peer_id = None
    if profile_file.exists():
        try:
            with open(profile_file, 'r', encoding='utf-8') as f:
                profile = json.load(f)
                my_peer_id = profile.get("peer_id")
        except Exception as e:
            print(f"Warning: Could not read profile.json: {e}")
    
    for msg in all_messages:
        sender_id = msg.get("sender_id", "")
        receiver_id = msg.get("receiver_id", "")
        
        if not sender_id or not receiver_id:
            print(f"Warning: Message with missing sender/receiver: {msg}")
            continue
        
        if sender_id == my_peer_id:
            peer_id = receiver_id
        else:
            peer_id = sender_id
        
        if peer_id not in grouped_by_peer:
            grouped_by_peer[peer_id] = []
        
        grouped_by_peer[peer_id].append(msg)
    
    print(f"\nGrouped messages into {len(grouped_by_peer)} peer conversations")
    
    chats_dir = user_dir / "chats"
    chats_dir.mkdir(exist_ok=True)
    
    for peer_id, messages in grouped_by_peer.items():
        peer_chat_dir = chats_dir / peer_id
        peer_chat_dir.mkdir(exist_ok=True)
        
        peer_messages_file = peer_chat_dir / "messages.json"
        
        print(f"  Writing {len(messages)} messages to {peer_messages_file}")
        
        with open(peer_messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        
        files_dir = peer_chat_dir / "files"
        files_dir.mkdir(exist_ok=True)
    
    print(f"\n✓ Migration complete for {username}")
    print(f"  - Original messages.json backed up to: {backup_file}")
    print(f"  - Migrated {len(grouped_by_peer)} peer conversations to: {chats_dir}")
    print(f"  - You can safely delete messages.json if everything looks good")

def migrate_all_users():
    data_dir = Path("data")
    if not data_dir.exists():
        print("No data directory found")
        return
    
    users = [d for d in data_dir.iterdir() if d.is_dir()]
    
    if not users:
        print("No user directories found in data/")
        return
    
    print(f"Found {len(users)} user(s) to migrate:")
    for user_dir in users:
        print(f"  - {user_dir.name}")
    
    for user_dir in users:
        migrate_user_data(user_dir.name)
    
    print("\n=== All migrations complete ===")

if __name__ == "__main__":
    print("=" * 60)
    print("Message Migration Script")
    print("=" * 60)
    print("\nThis script will migrate messages from the old format:")
    print("  data/{user}/messages.json")
    print("\nTo the new per-peer format:")
    print("  data/{user}/chats/{peer_id}/messages.json")
    print("\nA backup will be created before migration.")
    print("=" * 60)
    
    input("\nPress Enter to start migration...")
    
    migrate_all_users()
    
    print("\n✓ Done!")

