from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import List, Optional

from Core.models.message import Message

log = logging.getLogger(__name__)

class PeerMessageStorage:
    
    def __init__(self, user_root: Path, peer_identifier: str):
        self.user_root = user_root
        self.peer_identifier = peer_identifier
        self.chat_dir = user_root / "chats" / peer_identifier
        self.chat_dir.mkdir(parents=True, exist_ok=True)
        self.messages_file = self.chat_dir / "messages.json"
        self.files_dir = self.chat_dir / "files"
        self._lock = threading.RLock()
    
    def _ensure_files_dir(self):
        if not self.files_dir.exists():
            self.files_dir.mkdir(parents=True, exist_ok=True)
    
    def append_message(self, message: Message):
        with self._lock:
            messages = self._load_raw_messages()
            messages.append(message.to_dict())
            self._save_raw_messages(messages)
    
    def load_messages(self) -> List[Message]:
        with self._lock:
            raw_messages = self._load_raw_messages()
            return [Message.from_dict(item) for item in raw_messages]
    
    def _load_raw_messages(self) -> List[dict]:
        if not self.messages_file.exists():
            return []
        try:
            with self.messages_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def _save_raw_messages(self, messages: List[dict]):
        try:
            self.messages_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log.error(f"Failed to create directory {self.messages_file.parent}: {e}")
            raise
        
        try:
            with self.messages_file.open("w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"Failed to save messages to {self.messages_file}: {e}")
            raise
    
    def get_files_dir(self) -> Path:
        self._ensure_files_dir()
        return self.files_dir
    
    def save_file(self, file_name: str, file_data: bytes) -> Path:
        self._ensure_files_dir()
        file_path = self.files_dir / file_name
        
        counter = 1
        original_name = file_name
        while file_path.exists():
            name, ext = os.path.splitext(original_name)
            file_name = f"{name}_{counter}{ext}"
            file_path = self.files_dir / file_name
            counter += 1
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        return file_path

