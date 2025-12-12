from __future__ import annotations

import logging
import time
import base64
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from Core.routing.message_router import MessageRouter
from Core.models.message import Message
from Core.models.peer_info import PeerInfo
from Core.call.call_manager import CallManager, CallType, CallState

log = logging.getLogger(__name__)

class CoreSignals(QObject):
    
    message_received = Signal(dict)
    peer_updated = Signal(dict)
    friend_request_received = Signal(str, str)
    friend_accepted = Signal(str)
    friend_rejected = Signal(str)
    
    call_request_received = Signal(str, str, str)
    call_accepted = Signal(str)
    call_rejected = Signal(str)
    call_ended = Signal(str)
    remote_video_frame = Signal(bytes)

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
    ):
        
        self.username = username
        self.display_name = display_name
        self.tcp_port = tcp_port
        
        self.signals = CoreSignals()

        self.router = MessageRouter()
        self.peer_id = self.router.peer_id
        self.local_ip = ""
        self._running = False
        self.call_manager = CallManager()
        self.call_manager.on_call_state_changed = self._on_call_state_changed
        self.call_manager.on_remote_video_frame = self._on_remote_video_frame
        self.call_manager.on_error = self._on_call_error

    def start(self):
        if self._running:
            return

        self.router.set_peer_callback(self._handle_peer_update)
        self.router.set_friend_request_callback(self._handle_friend_request)
        self.router.set_friend_accepted_callback(self._handle_friend_accepted)
        self.router.set_friend_rejected_callback(self._handle_friend_rejected)

        self.router.set_call_request_callback(self._handle_call_request)
        self.router.set_call_accept_callback(self._handle_call_accept)
        self.router.set_call_reject_callback(self._handle_call_reject)
        self.router.set_call_end_callback(self._handle_call_end)

        self.router.connect_core(self.username, self.display_name, self.tcp_port, self._handle_router_message)

        self.peer_id = self.router.peer_id
        self.tcp_port = self.router.tcp_port

        from Core.utils.network_mode import get_local_ip
        self.local_ip = get_local_ip()
        log.info("Local IP: %s", self.local_ip)

        self.router.local_ip = self.local_ip

        self._running = True
        log.info("ChatCore started successfully (peer_id: %s, tcp_port: %s, local_ip: %s)", 
                self.peer_id, self.tcp_port, self.local_ip)

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

    def get_message_history(self, peer_id: str) -> List[Dict]:
        history = self.router.get_message_history(peer_id)
        return [self._message_to_dict(msg) for msg in history]
    
    def add_peer_by_ip(self, ip: str, port: int, display_name: str = "Unknown") -> Tuple[bool, Optional[str]]:
        return self.router.add_peer_by_ip(ip, port, display_name)
    
    def send_friend_request(self, peer_id: str) -> bool:
        
        return self.router.send_friend_request(peer_id)
    
    def accept_friend(self, peer_id: str) -> bool:
        
        return self.router.send_friend_accept(peer_id)
    
    def reject_friend(self, peer_id: str) -> bool:
        
        return self.router.send_friend_reject(peer_id)
    
    def start_call(self, peer_id: str, call_type: str) -> bool:
        peers = self.router.get_known_peers()
        peer = next((p for p in peers if p.peer_id == peer_id), None)
        
        if not peer:
            log.warning(f"[Call] Cannot call unknown peer {peer_id}")
            return False
        
        if not peer.ip or peer.status != "online":
            log.warning(f"[Call] Cannot call offline peer {peer.display_name}")
            return False
        
        call_type_enum = CallType.VIDEO if call_type == "video" else CallType.VOICE
        success, audio_port, video_port = self.call_manager.start_outgoing_call(
            peer_id, peer.display_name, peer.ip, call_type_enum
        )
        
        if not success:
            return False
        
        call_request_msg = Message.create_call_request(
            sender_id=self.peer_id,
            sender_name=self.display_name,
            receiver_id=peer_id,
            call_type=call_type,
            audio_port=audio_port,
            video_port=video_port
        )
        
        return self.router.peer_client.send(peer.ip, peer.tcp_port, call_request_msg)
    
    def accept_call(self, peer_id: str) -> bool:
        peers = self.router.get_known_peers()
        peer = next((p for p in peers if p.peer_id == peer_id), None)
        
        if not peer:
            log.warning(f"[Call] Cannot accept call from unknown peer")
            return False
        
        success, audio_port, video_port = self.call_manager.accept_incoming_call()
        
        if not success:
            return False
        
        accept_msg = Message.create_call_accept(
            sender_id=self.peer_id,
            sender_name=self.display_name,
            receiver_id=peer_id,
            audio_port=audio_port,
            video_port=video_port
        )
        
        sent = self.router.peer_client.send(peer.ip, peer.tcp_port, accept_msg)
        
        if sent:
            media_started = self.call_manager.start_media_streams(
                self.call_manager.peer_audio_port,
                self.call_manager.peer_video_port
            )
            
            if not media_started:
                log.error("[Call] Failed to start media streams, ending call")
                self.call_manager.end_call()
                return False
        else:
            self.call_manager.end_call()
            return False
        
        return True
    
    def reject_call(self, peer_id: str) -> bool:
        peer_ip = None
        peer_port = None
        
        peers = self.router.get_known_peers()
        peer = next((p for p in peers if p.peer_id == peer_id), None)
        
        if peer:
            peer_ip = peer.ip
            peer_port = peer.tcp_port
        elif self.call_manager.peer_ip:
            peer_ip = self.call_manager.peer_ip
            peer_port = 55000
        
        if not peer_ip:
            return False
        
        reject_msg = Message.create_call_reject(
            sender_id=self.peer_id,
            sender_name=self.display_name,
            receiver_id=peer_id
        )
        
        self.call_manager.peer_id = None
        self.call_manager.peer_name = None
        self.call_manager.peer_ip = None
        self.call_manager.call_type = None
        
        return self.router.peer_client.send(peer_ip, peer_port, reject_msg)
    
    def end_call(self) -> bool:
        if not self.call_manager.is_in_call():
            return False
        
        peer_id = self.call_manager.peer_id
        
        peers = self.router.get_known_peers()
        peer = next((p for p in peers if p.peer_id == peer_id), None)
        
        if peer:
            end_msg = Message.create_call_end(
                sender_id=self.peer_id,
                sender_name=self.display_name,
                receiver_id=peer_id
            )
            self.router.peer_client.send(peer.ip, peer.tcp_port, end_msg)
        
        self.call_manager.end_call()
        self.signals.call_ended.emit(peer_id)
        
        return True
    
    def _on_call_state_changed(self, state: CallState):
        log.info(f"[Call] State changed to {state.value}")
    
    def _on_remote_video_frame(self, frame_bytes: bytes):
        self.signals.remote_video_frame.emit(frame_bytes)
    
    def _on_call_error(self, error: str):
        log.error(f"[Call] Error: {error}")
    
    def _handle_call_request(self, peer_id: str, peer_name: str, call_type: str,
                            audio_port: int, video_port: int, peer_ip: str):
        log.info(f"[Call] Incoming {call_type} call from {peer_name}")
        
        call_type_enum = CallType.VIDEO if call_type == "video" else CallType.VOICE
        can_accept = self.call_manager.prepare_incoming_call(
            peer_id, peer_name, peer_ip, call_type_enum, audio_port, video_port
        )
        
        if can_accept:
            self.signals.call_request_received.emit(peer_id, peer_name, call_type)
        else:
            log.warning(f"[Call] Cannot accept call - already in call")
            self.reject_call(peer_id)
    
    def _handle_call_accept(self, peer_id: str, audio_port: int, video_port: int):
        log.info(f"[Call] Call accepted by peer")
        
        success = self.call_manager.start_media_streams(audio_port, video_port)
        
        if success:
            self.signals.call_accepted.emit(peer_id)
        else:
            log.error("[Call] Failed to start media streams after accept")
            self.call_manager.end_call()
            self.signals.call_rejected.emit(peer_id)
    
    def _handle_call_reject(self, peer_id: str):
        log.info(f"[Call] Call rejected by peer")
        
        self.call_manager.end_call()
        
        self.signals.call_rejected.emit(peer_id)
    
    def _handle_call_end(self, peer_id: str):
        log.info(f"[Call] Call ended by peer")
        
        self.call_manager.end_call()
        
        self.signals.call_ended.emit(peer_id)

    def _handle_router_message(self, message: Message):
        
        self._emit_message(message)

    def _emit_message(self, message: Message):
        
        payload = self._message_to_dict(message)
        self.signals.message_received.emit(payload)

    def _handle_peer_update(self, peer_info: PeerInfo):
        
        peer_dict = self._peer_to_dict(peer_info)
        self.signals.peer_updated.emit(peer_dict)
    
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
            "status": peer.status,
            "avatar_path": peer.avatar_path,
        }

    def _message_to_dict(self, message: Message) -> Dict:
        is_sender = bool(self.peer_id and message.sender_id == self.peer_id)
        
        peer_id = message.receiver_id if is_sender else message.sender_id
        
        local_file_path = None

        try:
            if getattr(message, "file_name", None) and self.router and self.router.data_manager:
                files_dir = self.router.data_manager.get_peer_files_dir(peer_id)
                candidate = files_dir / message.file_name

                if not candidate.exists() and getattr(message, "file_data", None):
                    try:
                        file_bytes = base64.b64decode(message.file_data)
                        candidate = self.router.data_manager.save_file_for_peer(peer_id, message.file_name, file_bytes)
                    except Exception:
                        candidate = files_dir / message.file_name

                if candidate.exists():
                    local_file_path = str(candidate)
        except Exception:
            pass

        content = message.content
        peer_avatar_path = None
        
        if message.msg_type in ("text", "image", "file") and content:
            try:
                content_data = json.loads(content)
                if isinstance(content_data, dict) and "text" in content_data:
                    content = content_data["text"]
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        
        if not is_sender:
            peer_info = self.router._peers.get(peer_id) if self.router else None
            if peer_info:
                peer_avatar_path = peer_info.avatar_path

        return {
            "message_id": message.message_id,
            "peer_id": peer_id,
            "sender_id": message.sender_id,
            "sender_name": message.sender_name,
            "content": content,
            "timestamp": message.timestamp,
            "time_str": _format_time(message.timestamp),
            "date_str": _format_date(message.timestamp),
            "is_sender": is_sender,
            "msg_type": message.msg_type,
            "file_name": getattr(message, 'file_name', None),
            "file_data": getattr(message, 'file_data', None),
            "audio_data": getattr(message, 'audio_data', None),
            "local_file_path": local_file_path,
            "peer_avatar_path": peer_avatar_path,
        }
