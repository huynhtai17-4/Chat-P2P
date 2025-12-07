from __future__ import annotations

import logging
import time
from typing import Callable, Dict, List, Optional

try:
    from PySide6.QtCore import QObject, Signal
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QObject = object
    Signal = None

from Core.routing.message_router import MessageRouter
from Core.models.message import Message
from Core.models.peer_info import PeerInfo

log = logging.getLogger(__name__)

class CoreSignals(QObject):
    
    message_received = Signal(dict)  # payload dict
    peer_updated = Signal(dict)  # peer_info dict
    temp_peer_updated = Signal(dict)  # peer_info dict
    temp_peer_removed = Signal(str)  # peer_id
    friend_request_received = Signal(str, str)  # peer_id, display_name
    friend_accepted = Signal(str)  # peer_id
    friend_rejected = Signal(str)  # peer_id

def _format_time(ts: float) -> str:
    return time.strftime("%H:%M", time.localtime(ts))

def _format_date(ts: float) -> str:
    return time.strftime("%d %b %Y", time.localtime(ts))

class ChatCore:

    def __init__(
        self,
        username: str,
        display_name: str,
        tcp_port: int,
        on_message_callback: Optional[Callable[[Dict], None]] = None,
        on_peer_update: Optional[Callable[[Dict], None]] = None,
    ):
        
        self.username = username
        self.display_name = display_name
        self.tcp_port = tcp_port
        
        self.signals = CoreSignals()
        
        self._on_message_callback = on_message_callback
        self._on_peer_update = on_peer_update
        self._on_temp_peer_update: Optional[Callable[[Dict], None]] = None
        self._on_friend_request: Optional[Callable[[str, str], None]] = None  # peer_id, display_name
        self._on_friend_accepted: Optional[Callable[[str], None]] = None  # peer_id
        self._on_friend_rejected: Optional[Callable[[str], None]] = None  # peer_id

        self.router = MessageRouter()
        self.peer_id = self.router.peer_id
        self._running = False

    def start(self):
        
        if self._running:
            return
        
        self.router.set_peer_callback(self._handle_peer_update)
        self.router.set_temp_peer_callback(self._handle_temp_peer_update)
        self.router.set_temp_peer_removed_callback(self._handle_temp_peer_removed)
        self.router.set_friend_request_callback(self._handle_friend_request)
        self.router.set_friend_accepted_callback(self._handle_friend_accepted)
        self.router.set_friend_rejected_callback(self._handle_friend_rejected)
        
        self.router.connect_core(self.username, self.display_name, self.tcp_port, self._handle_router_message)
        
        self.peer_id = self.router.peer_id
        self.tcp_port = self.router.tcp_port
        
        self._running = True
        log.info("ChatCore started successfully (peer_id: %s, tcp_port: %s)", self.peer_id, self.tcp_port)

    def stop(self):
        if not self._running:
            return
        self.router.stop()
        self._running = False

    def send_message(self, peer_id: str, content: str, msg_type: str = "text", 
                     file_name: str = None, file_data: str = None, audio_data: str = None) -> bool:
        success, message = self.router.send_message(peer_id, content, msg_type=msg_type, 
                                                     file_name=file_name, file_data=file_data, audio_data=audio_data)
        if success and message:
            self._emit_message(message)
        return success

    def get_known_peers(self) -> List[Dict]:
        peers = self.router.get_known_peers()
        return [self._peer_to_dict(peer) for peer in peers]

    def get_message_history(self, peer_id: Optional[str] = None) -> List[Dict]:
        history = self.router.get_message_history(peer_id)
        return [self._message_to_dict(msg) for msg in history]
    
    def add_peer(self, peer_id: str) -> bool:
        
        return self.router.add_peer(peer_id)
    
    def get_temp_discovered_peers(self) -> List[Dict]:
        
        peers = self.router.get_temp_discovered_peers()
        return [self._peer_to_dict(peer) for peer in peers]
    
    def remove_temp_peer(self, peer_id: str) -> bool:
        
        return self.router.remove_temp_peer(peer_id)
    
    def set_temp_peer_update_callback(self, callback: Optional[Callable[[Dict], None]]):
        
        self._on_temp_peer_update = callback
    
    def set_friend_request_callback(self, callback: Optional[Callable[[str, str], None]]):
        
        self._on_friend_request = callback
    
    def set_friend_accepted_callback(self, callback: Optional[Callable[[str], None]]):
        
        self._on_friend_accepted = callback
    
    def set_friend_rejected_callback(self, callback: Optional[Callable[[str], None]]):
        
        self._on_friend_rejected = callback
    
    def send_friend_request(self, peer_id: str) -> bool:
        
        return self.router.send_friend_request(peer_id)
    
    def accept_friend(self, peer_id: str) -> bool:
        
        return self.router.send_friend_accept(peer_id)
    
    def reject_friend(self, peer_id: str) -> bool:
        
        return self.router.send_friend_reject(peer_id)
    
    def cleanup_offline_peers(self, max_offline_time: float = 600.0) -> int:
        
        return self.router.cleanup_offline_peers(max_offline_time)

    def _handle_router_message(self, message: Message):
        
        self._emit_message(message)

    def _emit_message(self, message: Message):
        
        payload = self._message_to_dict(message)
        self.signals.message_received.emit(payload)

    def _handle_peer_update(self, peer_info: PeerInfo):
        
        peer_dict = self._peer_to_dict(peer_info)
        self.signals.peer_updated.emit(peer_dict)
    
    def _handle_temp_peer_update(self, peer_info: PeerInfo):
        
        peer_dict = self._peer_to_dict(peer_info)
        self.signals.temp_peer_updated.emit(peer_dict)
    
    def _handle_temp_peer_removed(self, peer_id: str):
        
        self.signals.temp_peer_removed.emit(peer_id)
    
    def _handle_friend_request(self, peer_id: str, display_name: str):
        
        self.signals.friend_request_received.emit(peer_id, display_name)
    
    def _handle_friend_accepted(self, peer_id: str):
        
        self.signals.friend_accepted.emit(peer_id)
    
    def _handle_friend_rejected(self, peer_id: str):
        
        self.signals.friend_rejected.emit(peer_id)

    def _peer_to_dict(self, peer: PeerInfo) -> Dict:
        return {
            "peer_id": peer.peer_id,
            "display_name": peer.display_name,
            "ip": peer.ip,
            "tcp_port": peer.tcp_port,
            "last_seen": peer.last_seen,
            "status": peer.status,
        }

    def _message_to_dict(self, message: Message) -> Dict:
        peer_id = message.receiver_id if message.sender_id == self.peer_id else message.sender_id
        return {
            "message_id": message.message_id,
            "peer_id": peer_id,
            "sender_id": message.sender_id,
            "sender_name": message.sender_name,
            "content": message.content,
            "timestamp": message.timestamp,
            "time_str": _format_time(message.timestamp),
            "date_str": _format_date(message.timestamp),
            "is_sender": message.sender_id == self.peer_id,
            "file_name": getattr(message, 'file_name', None),
            "file_data": getattr(message, 'file_data', None),
            "audio_data": getattr(message, 'audio_data', None),
        }
