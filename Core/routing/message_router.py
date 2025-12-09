from __future__ import annotations

import logging
import threading
import uuid
from typing import Callable, Dict, List, Optional, Tuple

from Core.models.message import Message
from Core.models.peer_info import PeerInfo
from Core.networking.peer_client import PeerClient
from Core.networking.peer_listener import PeerListener
from Core.storage.data_manager import DataManager
from Core.utils import config
from Core.routing.message_handlers import MessageHandlers
from Core.routing.friend_request_manager import FriendRequestManager
from Core.routing.peer_manager import PeerManager
from Core.routing.status_broadcaster import StatusBroadcaster

log = logging.getLogger(__name__)

class MessageRouter:

    def __init__(self):
        self.peer_id: Optional[str] = None
        self.display_name: Optional[str] = None
        self.tcp_port = config.TCP_BASE_PORT

        self.data_manager: Optional[DataManager] = None
        self.peer_listener: Optional[PeerListener] = None
        self.peer_client = PeerClient()

        self._on_message_callback: Optional[Callable[[Message], None]] = None
        self._on_peer_callback: Optional[Callable[[PeerInfo], None]] = None
        self._on_friend_request_callback: Optional[Callable[[str, str], None]] = None
        self._on_friend_accepted_callback: Optional[Callable[[str], None]] = None
        self._on_friend_rejected_callback: Optional[Callable[[str], None]] = None
        self._lock = threading.RLock()
        
        self._peers: Dict[str, PeerInfo] = {}
        self._outgoing_requests: set[str] = set()
        self._incoming_requests: set[str] = set()
        self._friend_request_emitted: set[str] = set()
        self._peer_send_failures: Dict[str, int] = {}
        
        self.message_handlers = MessageHandlers(self)
        self.friend_request_manager = FriendRequestManager(self)
        self.peer_manager = PeerManager(self)
        self.status_broadcaster = StatusBroadcaster(self)

    def connect_core(self, username: str, display_name: str, tcp_port: int, on_message_callback: Callable[[Message], None]):
        self.display_name = display_name
        self._on_message_callback = on_message_callback

        self.data_manager = DataManager(username)
        profile = self.data_manager.load_profile()
        
        saved_peer_id = profile.get("peer_id")
        if saved_peer_id and isinstance(saved_peer_id, str) and len(saved_peer_id) > 0:
            self.peer_id = saved_peer_id
            log.info("Loaded peer_id %s from profile.json", self.peer_id)
        else:
            self.peer_id = str(uuid.uuid4())
            log.info("Generated new peer_id %s (saving to profile)", self.peer_id)
        
        saved_tcp_port = profile.get("tcp_port")
        if saved_tcp_port and isinstance(saved_tcp_port, int) and saved_tcp_port > 0:
            self.tcp_port = saved_tcp_port
            log.info("Loaded TCP port %s from profile.json", self.tcp_port)
        else:
            self.tcp_port = tcp_port
            log.info("Using provided TCP port %s (saving to profile)", self.tcp_port)
        
        profile.update({"display_name": display_name, "peer_id": self.peer_id, "tcp_port": self.tcp_port})
        self.data_manager.save_profile(profile)

        def message_handler(msg, ip, port):
            self._handle_incoming_message_with_addr(msg, ip, port)
        
        self.peer_listener = PeerListener(self.peer_id, self.data_manager, message_handler)
        try:
            desired_port = self.tcp_port
            actual_port = None
            for try_port in [desired_port] + list(range(55000, 55200)):
                try:
                    actual_port = self.peer_listener.start(port=try_port)
                    break
                except RuntimeError as e:
                    log.warning("Port %s unavailable (%s). Trying next...", try_port, e)
                    continue
            if actual_port is None:
                raise RuntimeError("No available TCP port in range 55000-55199")

            if actual_port != self.tcp_port:
                log.warning("TCP port changed from %s to %s (port was in use)", self.tcp_port, actual_port)
                self.tcp_port = actual_port
                profile = self.data_manager.load_profile()
                profile["tcp_port"] = actual_port
                self.data_manager.save_profile(profile)
            
            import time
            time.sleep(0.1)
            if not self.peer_listener._thread or not self.peer_listener._thread.is_alive():
                raise RuntimeError("TCP Listener thread not running after start()")
            log.info("[TCP] Listener started on port %s", self.tcp_port)
        except Exception as e:
            log.error("Failed to start PeerListener: %s", e)
            raise RuntimeError(f"Failed to start TCP listener: {e}")

        if self.data_manager:
            self._peers = self.data_manager.load_peers()
            for peer in self._peers.values():
                peer.status = "offline"
            log.info("Loaded %s friends from peers.json (all set to offline initially)", len(self._peers))
            for peer_id, peer in self._peers.items():
                log.info("  - Friend: %s (%s) at %s:%s", peer.display_name, peer_id[:8], peer.ip, peer.tcp_port)
        
        self._notify_existing_peers()
        
        import time
        time.sleep(0.2)
        log.info("[STARTUP] Broadcasting ONLINE status to all friends...")
        self.status_broadcaster.broadcast_status("online")
        
        log.info("MessageRouter ready as %s (%s)", self.display_name, self.peer_id)

    def stop(self):
        self.status_broadcaster.broadcast_status("offline")
        if self.peer_listener:
            self.peer_listener.stop()

    def _handle_incoming_message_with_addr(self, message: Message, sender_ip: str = "", sender_port: int = 0):
        self._handle_incoming_message(message, sender_ip, sender_port)
    
    def _handle_incoming_message(self, message: Message, sender_ip: str = "", sender_port: int = 0):
        msg_type = message.msg_type
        
        if msg_type == "FRIEND_REQUEST":
            self.message_handlers.handle_friend_request(message, sender_ip)
            return
        elif msg_type == "FRIEND_ACCEPT":
            self.message_handlers.handle_friend_accept(message, sender_ip)
            return
        elif msg_type == "FRIEND_SYNC":
            self.message_handlers.handle_friend_sync(message, sender_ip)
            return
        elif msg_type == "ONLINE" or msg_type == "OFFLINE":
            self.message_handlers.handle_status_message(message, sender_ip)
            return
        elif msg_type == "FRIEND_REJECT":
            self.message_handlers.handle_friend_reject(message)
            return
        elif msg_type == "HELLO":
            self.message_handlers.handle_hello(message, sender_ip, sender_port)
            return
        elif msg_type == "HELLO_REPLY":
            self.message_handlers.handle_hello_reply(message, sender_ip)
            return
        
        # Block messages from peers not in friends list (after unfriend)
        with self._lock:
            if message.sender_id not in self._peers:
                log.debug("[BLOCK] Ignored message from %s (not in friends list)", message.sender_id)
                return
        
        log.info("Message from %s (%s): %s", message.sender_name, message.sender_id, message.content)
        
        peer_id = message.sender_id if message.sender_id != self.peer_id else message.receiver_id
        
        if self.data_manager:
            try:
                if message.msg_type in ("file", "image") and getattr(message, "file_name", None) and getattr(message, "file_data", None):
                    import base64
                    file_bytes = base64.b64decode(message.file_data)
                    self.data_manager.save_file_for_peer(peer_id, message.file_name, file_bytes)
            except Exception:
                pass

            self.data_manager.append_message(message, peer_id)
        
        if self._on_message_callback:
            self._on_message_callback(message)

    def send_message(self, to_peer_id: str, content: str, msg_type: str = "text",
                     file_name: str = None, file_data: str = None, audio_data: str = None) -> Tuple[bool, Optional[Message]]:
        
        if not self.data_manager:
            log.error("Router not initialized. Cannot send message.")
            raise RuntimeError("Router not initialized.")

        if not self.peer_listener or not self.peer_listener._thread or not self.peer_listener._thread.is_alive():
            log.error("PeerListener not running. Cannot send message.")
            return False, None

        with self._lock:
            target = self._peers.get(to_peer_id)
        if not target:
            log.warning("Cannot send message to %s: Peer not in friends list", to_peer_id)
            return False, None

        if not target.ip or not target.tcp_port:
            log.warning("Cannot send message to %s: Invalid IP (%s) or port (%s)", to_peer_id, target.ip, target.tcp_port)
            return False, None

        if target.ip == "0.0.0.0" or target.ip == "":
            log.warning("Cannot send message to %s: Invalid IP address", to_peer_id)
            return False, None

        if target.tcp_port == 0 or target.tcp_port < 55000 or target.tcp_port > 55199:
            log.warning("Cannot send message to %s: Invalid port %s", to_peer_id, target.tcp_port)
            return False, None

        message = Message.create(
            sender_id=self.peer_id,
            sender_name=self.display_name or "Unknown",
            receiver_id=to_peer_id,
            content=content,
            msg_type=msg_type,
            file_name=file_name,
            file_data=file_data,
            audio_data=audio_data,
        )

        log.info("Sending message to %s (%s) at %s:%s", target.display_name, to_peer_id, target.ip, target.tcp_port)
        success = self.peer_client.send(target.ip, target.tcp_port, message)
        if success:
            self._peer_send_failures.pop(to_peer_id, None)
            if self.data_manager:
                self.data_manager.append_message(message, to_peer_id)
                try:
                    if msg_type in ("file", "image") and file_name and file_data:
                        import base64
                        file_bytes = base64.b64decode(file_data)
                        self.data_manager.save_file_for_peer(to_peer_id, file_name, file_bytes)
                except Exception:
                    pass
            log.info("Message sent successfully to %s (%s)", target.display_name, to_peer_id)
        else:
            failures = self._peer_send_failures.get(to_peer_id, 0) + 1
            self._peer_send_failures[to_peer_id] = failures
            log.warning("Failed to send message to %s (%s) - connection refused or offline", to_peer_id, target.display_name)
        return success, message if success else None

    def get_known_peers(self) -> List[PeerInfo]:
        return self.peer_manager.get_known_peers()

    def get_message_history(self, peer_id: str) -> List[Message]:
        if not self.data_manager:
            return []
        return self.data_manager.load_messages(peer_id=peer_id)

    def set_peer_callback(self, callback: Optional[Callable[[PeerInfo], None]]):
        self._on_peer_callback = callback

    def add_peer(self, peer_id: str) -> bool:
        return self.peer_manager.add_peer(peer_id)
    
    def add_peer_by_ip(self, ip: str, port: int, display_name: str = "Unknown") -> Tuple[bool, Optional[str]]:
        """
        Add a friend directly by IP and port without discovery.
        Returns (success, peer_id or error_message)
        """
        print(f"[Add Peer] Request to add peer at {ip}:{port} with name '{display_name}'")
        print(f"[Add Peer] My peer_id={self.peer_id}, my name={self.display_name}")
        log.info(f"[Add Peer] Request to add peer at {ip}:{port} with name '{display_name}'")
        log.info(f"[Add Peer] My peer_id={self.peer_id}, my name={self.display_name}")
        
        if not ip or not port:
            log.error("[Add Peer] Invalid IP or port")
            return False, "Invalid IP or port"
        
        if port < 1 or port > 65535:
            log.error(f"[Add Peer] Port {port} out of valid range")
            return False, "Port must be between 1 and 65535"
        
        # Generate a temporary peer_id; will be replaced when we receive HELLO response
        temp_peer_id = str(uuid.uuid4())
        
        peer_info = PeerInfo(
            peer_id=temp_peer_id,
            display_name=display_name,
            ip=ip,
            tcp_port=port,
            status="offline"
        )
        
        with self._lock:
            self._peers[temp_peer_id] = peer_info
        
        if self.data_manager:
            self.data_manager.update_peer(peer_info)
            print(f"[Add Peer] Added peer {display_name} ({temp_peer_id[:8]}) at {ip}:{port}")
            log.info("Added peer %s (%s) at %s:%s", display_name, temp_peer_id, ip, port)
        
        # Send HELLO handshake to verify peer exists and get peer info
        try:
            print(f"[Add Peer] Creating HELLO message to send to {ip}:{port}")
            # Get our real IP (the one we're listening on)
            my_ip = getattr(self, 'local_ip', '')
            print(f"[Add Peer] Router has local_ip attribute: {hasattr(self, 'local_ip')}")
            print(f"[Add Peer] My IP (for HELLO): {my_ip}")
            print(f"[Add Peer] Including our IP in HELLO: {my_ip}:{self.tcp_port}")
            hello_msg = Message.create_hello(
                sender_id=self.peer_id,
                sender_name=self.display_name or "Unknown",
                receiver_id=temp_peer_id,
                tcp_port=self.tcp_port,
                sender_ip=my_ip  # Include our real IP
            )
            print(f"[Add Peer] Sending HELLO to {ip}:{port}...")
            success = self.peer_client.send(ip, port, hello_msg)
            if success:
                print(f"[Add Peer] ✓ Sent HELLO handshake to {ip}:{port}")
                log.info("Sent HELLO handshake to %s:%s", ip, port)
            else:
                print(f"[Add Peer] ✗ Failed to send HELLO to {ip}:{port} (peer may be offline)")
                log.warning("Failed to send HELLO to %s:%s (peer may be offline)", ip, port)
        except Exception as e:
            print(f"[Add Peer] ✗ Error sending HELLO to {ip}:{port}: {e}")
            import traceback
            traceback.print_exc()
            log.warning("Error sending HELLO to %s:%s: %s", ip, port, e)
        
        if self._on_peer_callback:
            try:
                print(f"[Add Peer] Calling _on_peer_callback for {display_name}")
                self._on_peer_callback(peer_info)
            except Exception as e:
                print(f"[Add Peer] Error in _on_peer_callback: {e}")
                log.error("Error in _on_peer_callback for new peer: %s", e, exc_info=True)
        
        print(f"[Add Peer] Returning success=True, peer_id={temp_peer_id[:8]}...")
        return True, temp_peer_id
    
    def set_friend_request_callback(self, callback: Optional[Callable[[str, str], None]]):
        self._on_friend_request_callback = callback
    
    def set_friend_accepted_callback(self, callback: Optional[Callable[[str], None]]):
        self._on_friend_accepted_callback = callback
    
    def set_friend_rejected_callback(self, callback: Optional[Callable[[str], None]]):
        self._on_friend_rejected_callback = callback
    
    def send_friend_request(self, peer_id: str) -> bool:
        return self.friend_request_manager.send_friend_request(peer_id)
    
    def send_friend_accept(self, peer_id: str) -> bool:
        return self.friend_request_manager.send_friend_accept(peer_id)
    
    def send_friend_reject(self, peer_id: str) -> bool:
        return self.friend_request_manager.send_friend_reject(peer_id)

    def _notify_existing_peers(self):
        self.peer_manager.notify_existing_peers()
    
    def _get_local_ip_for_sync(self) -> str:
        """Get local IP address for FRIEND_SYNC messages"""
        try:
            from Core.utils.network_mode import get_local_ip
            return get_local_ip()
        except Exception:
            return ""
