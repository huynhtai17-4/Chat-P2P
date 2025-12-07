from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional

from Core.models.message import Message
from Core.models.peer_info import PeerInfo
from Core.utils import config

class DataManager:

    def __init__(self, username: str):
        
        self.username = username
        data_root = Path(os.getcwd()) / "data"
        self.root = data_root / username
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _read_json(self, filename: str, default):
        path = self.root / filename
        if not path.exists():
            return default
        with self._lock, path.open("r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default

    def _write_json(self, filename: str, data):
        path = self.root / filename
        with self._lock, path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_profile(self) -> Dict:
        return self._read_json(config.PROFILE_FILENAME, {})

    def save_profile(self, profile: Dict):
        self._write_json(config.PROFILE_FILENAME, profile)

    def load_peers(self) -> Dict[str, PeerInfo]:
        data = self._read_json(config.PEERS_FILENAME, {})
        peers = {}
        import logging
        log = logging.getLogger(__name__)
        for peer_id, info in data.items():
            try:
                peer_info = PeerInfo.from_dict(info)
                if not peer_info.tcp_port or peer_info.tcp_port < 55000 or peer_info.tcp_port > 55199:
                    log.warning("Skipping peer %s with invalid tcp_port %s (must be 55000-55199)", 
                               peer_id, peer_info.tcp_port)
                    continue
                peers[peer_id] = peer_info
            except Exception as e:
                log.warning("Failed to load peer %s: %s", peer_id, e)
        return peers

    def save_peers(self, peers: Dict[str, PeerInfo]):
        serializable = {peer_id: info.to_dict() for peer_id, info in peers.items()}
        self._write_json(config.PEERS_FILENAME, serializable)

    def update_peer(self, peer_info: PeerInfo):
        if not peer_info.tcp_port or peer_info.tcp_port < 55000 or peer_info.tcp_port > 55199:
            import logging
            log = logging.getLogger(__name__)
            log.warning("Cannot save peer %s: invalid tcp_port %s (must be 55000-55199). Skipping save.", 
                       peer_info.peer_id, peer_info.tcp_port)
            return
        
        peers = self.load_peers()
        peers[peer_info.peer_id] = peer_info
        self.save_peers(peers)
    
    def remove_peer(self, peer_id: str):
        
        peers = self.load_peers()
        if peer_id in peers:
            del peers[peer_id]
            self.save_peers(peers)

    def append_message(self, message: Message):
        messages = self._read_json(config.MESSAGES_FILENAME, [])
        messages.append(message.to_dict())
        self._write_json(config.MESSAGES_FILENAME, messages)

    def load_messages(self, peer_id: Optional[str] = None) -> List[Message]:
        raw_messages = self._read_json(config.MESSAGES_FILENAME, [])
        messages = [Message.from_dict(item) for item in raw_messages]
        if peer_id:
            messages = [msg for msg in messages if msg.sender_id == peer_id or msg.receiver_id == peer_id]
        return messages

    def load_settings(self) -> Dict:
        return self._read_json(config.SETTINGS_FILENAME, {})

    def save_settings(self, settings: Dict):
        self._write_json(config.SETTINGS_FILENAME, settings)
