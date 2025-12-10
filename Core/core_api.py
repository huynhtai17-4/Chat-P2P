from __future__ import annotations

import logging
import time
import base64
from typing import Callable, Dict, List, Optional, Tuple

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
from Core.call.call_manager import CallManager, CallType, CallState

log = logging.getLogger(__name__)

class CoreSignals(QObject):
    
    message_received = Signal(dict)  # payload dict
    peer_updated = Signal(dict)  # peer_info dict
    temp_peer_updated = Signal(dict)  # peer_info dict
    temp_peer_removed = Signal(str)  # peer_id
    friend_request_received = Signal(str, str)  # peer_id, display_name
    friend_accepted = Signal(str)  # peer_id
    friend_rejected = Signal(str)  # peer_id
    
    # Call signals
    call_request_received = Signal(str, str, str)  # peer_id, peer_name, call_type
    call_accepted = Signal(str)  # peer_id
    call_rejected = Signal(str)  # peer_id
    call_ended = Signal(str)  # peer_id
    remote_video_frame = Signal(bytes)  # JPEG frame bytes

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
        self.local_ip = ""
        self._running = False
        
        # Call manager
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
        
        # Set call callbacks
        self.router.set_call_request_callback(self._handle_call_request)
        self.router.set_call_accept_callback(self._handle_call_accept)
        self.router.set_call_reject_callback(self._handle_call_reject)
        self.router.set_call_end_callback(self._handle_call_end)
        
        self.router.connect_core(self.username, self.display_name, self.tcp_port, self._handle_router_message)
        
        self.peer_id = self.router.peer_id
        self.tcp_port = self.router.tcp_port
        
        # Get LAN IP for display and connection
        from Core.utils.network_mode import get_local_ip
        self.local_ip = get_local_ip()
        print(f"[ChatCore] My local_ip: {self.local_ip}")
        log.info("Local IP: %s", self.local_ip)
        
        # Pass local_ip to router so it can include in HELLO messages
        self.router.local_ip = self.local_ip
        print(f"[ChatCore] Set router.local_ip to: {self.router.local_ip}")
        
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
    
    def add_peer(self, peer_id: str) -> bool:
        # Legacy method - no longer used with Add Friend by IP
        return False
    
    def add_peer_by_ip(self, ip: str, port: int, display_name: str = "Unknown") -> Tuple[bool, Optional[str]]:
        """Add a friend directly by IP and port"""
        return self.router.add_peer_by_ip(ip, port, display_name)
    
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
        # Offline cleanup removed - status is runtime-only based on ONLINE/OFFLINE events
        return 0
    
    # ====== Call Methods ======
    
    def start_call(self, peer_id: str, call_type: str) -> bool:
        """Start a voice or video call
        Args:
            peer_id: ID of peer to call
            call_type: 'voice' or 'video'
        Returns:
            True if call started successfully
        """
        # Get peer info
        peers = self.router.get_known_peers()
        peer = next((p for p in peers if p.peer_id == peer_id), None)
        
        if not peer:
            log.warning(f"[Call] Cannot call unknown peer {peer_id}")
            return False
        
        if not peer.ip or peer.status != "online":
            log.warning(f"[Call] Cannot call offline peer {peer.display_name}")
            return False
        
        # Start outgoing call
        call_type_enum = CallType.VIDEO if call_type == "video" else CallType.VOICE
        success, audio_port, video_port = self.call_manager.start_outgoing_call(
            peer_id, peer.display_name, peer.ip, call_type_enum
        )
        
        if not success:
            return False
        
        # Send CALL_REQUEST message
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
        """Accept an incoming call"""
        # Get peer info
        peers = self.router.get_known_peers()
        peer = next((p for p in peers if p.peer_id == peer_id), None)
        
        if not peer:
            log.warning(f"[Call] Cannot accept call from unknown peer")
            return False
        
        # Accept the incoming call (this sets state to INCOMING and starts receivers)
        success, audio_port, video_port = self.call_manager.accept_incoming_call()
        
        if not success:
            return False
        
        # Send CALL_ACCEPT message
        accept_msg = Message.create_call_accept(
            sender_id=self.peer_id,
            sender_name=self.display_name,
            receiver_id=peer_id,
            audio_port=audio_port,
            video_port=video_port
        )
        
        sent = self.router.peer_client.send(peer.ip, peer.tcp_port, accept_msg)
        
        if sent:
            # Start media streams
            media_started = self.call_manager.start_media_streams(
                self.call_manager.peer_audio_port,
                self.call_manager.peer_video_port
            )
            
            if not media_started:
                log.error("[Call] Failed to start media streams, ending call")
                self.call_manager.end_call()
                return False
        else:
            # Failed to send accept message, cleanup
            self.call_manager.end_call()
            return False
        
        return True
    
    def reject_call(self, peer_id: str) -> bool:
        """Reject an incoming call"""
        # Get peer info from call manager if not in peers list yet
        peer_ip = None
        peer_port = None
        
        peers = self.router.get_known_peers()
        peer = next((p for p in peers if p.peer_id == peer_id), None)
        
        if peer:
            peer_ip = peer.ip
            peer_port = peer.tcp_port
        elif self.call_manager.peer_ip:
            # Use info from call manager
            peer_ip = self.call_manager.peer_ip
            # Need to find port - assume standard
            peer_port = 55000  # TODO: Get actual port
        
        if not peer_ip:
            return False
        
        reject_msg = Message.create_call_reject(
            sender_id=self.peer_id,
            sender_name=self.display_name,
            receiver_id=peer_id
        )
        
        # Clear call manager state
        self.call_manager.peer_id = None
        self.call_manager.peer_name = None
        self.call_manager.peer_ip = None
        self.call_manager.call_type = None
        
        return self.router.peer_client.send(peer_ip, peer_port, reject_msg)
    
    def end_call(self) -> bool:
        """End the current call"""
        if not self.call_manager.is_in_call():
            return False
        
        peer_id = self.call_manager.peer_id
        
        # Get peer info
        peers = self.router.get_known_peers()
        peer = next((p for p in peers if p.peer_id == peer_id), None)
        
        if peer:
            # Send CALL_END message
            end_msg = Message.create_call_end(
                sender_id=self.peer_id,
                sender_name=self.display_name,
                receiver_id=peer_id
            )
            self.router.peer_client.send(peer.ip, peer.tcp_port, end_msg)
        
        # End call in manager
        self.call_manager.end_call()
        self.signals.call_ended.emit(peer_id)
        
        return True
    
    def _on_call_state_changed(self, state: CallState):
        """Callback when call state changes"""
        log.info(f"[Call] State changed to {state.value}")
    
    def _on_remote_video_frame(self, frame_bytes: bytes):
        """Callback when remote video frame received"""
        self.signals.remote_video_frame.emit(frame_bytes)
    
    def _on_call_error(self, error: str):
        """Callback when call error occurs"""
        log.error(f"[Call] Error: {error}")
    
    def _handle_call_request(self, peer_id: str, peer_name: str, call_type: str,
                            audio_port: int, video_port: int, peer_ip: str):
        """Handle incoming call request from message router"""
        log.info(f"[Call] Incoming {call_type} call from {peer_name}")
        
        # Prepare incoming call (save info, don't change state yet)
        call_type_enum = CallType.VIDEO if call_type == "video" else CallType.VOICE
        can_accept = self.call_manager.prepare_incoming_call(
            peer_id, peer_name, peer_ip, call_type_enum, audio_port, video_port
        )
        
        if can_accept:
            # Emit signal to GUI to show incoming call dialog
            self.signals.call_request_received.emit(peer_id, peer_name, call_type)
        else:
            # Already in call, send REJECT automatically
            log.warning(f"[Call] Cannot accept call - already in call")
            self.reject_call(peer_id)
    
    def _handle_call_accept(self, peer_id: str, audio_port: int, video_port: int):
        """Handle call accept from message router"""
        log.info(f"[Call] Call accepted by peer")
        
        # Start media streams
        success = self.call_manager.start_media_streams(audio_port, video_port)
        
        if success:
            # Emit signal to GUI
            self.signals.call_accepted.emit(peer_id)
        else:
            # Failed to start media, cleanup and notify
            log.error("[Call] Failed to start media streams after accept")
            self.call_manager.end_call()
            self.signals.call_rejected.emit(peer_id)  # Reuse rejected signal to close dialogs
    
    def _handle_call_reject(self, peer_id: str):
        """Handle call reject from message router"""
        log.info(f"[Call] Call rejected by peer")
        
        # End call in manager
        self.call_manager.end_call()
        
        # Emit signal to GUI
        self.signals.call_rejected.emit(peer_id)
    
    def _handle_call_end(self, peer_id: str):
        """Handle call end from message router"""
        log.info(f"[Call] Call ended by peer")
        
        # End call in manager
        self.call_manager.end_call()
        
        # Emit signal to GUI
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
        }

    def _message_to_dict(self, message: Message) -> Dict:
        # Determine if this message was sent by the local peer
        is_sender = bool(self.peer_id and message.sender_id == self.peer_id)
        
        # Determine the peer_id (the other peer in the conversation)
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

        return {
            "message_id": message.message_id,
            "peer_id": peer_id,
            "sender_id": message.sender_id,
            "sender_name": message.sender_name,
            "content": message.content,
            "timestamp": message.timestamp,
            "time_str": _format_time(message.timestamp),
            "date_str": _format_date(message.timestamp),
            "is_sender": is_sender,
            "msg_type": message.msg_type,
            "file_name": getattr(message, 'file_name', None),
            "file_data": getattr(message, 'file_data', None),
            "audio_data": getattr(message, 'audio_data', None),
            "local_file_path": local_file_path,
        }
