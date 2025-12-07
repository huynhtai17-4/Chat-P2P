from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Callable, Dict, List, Optional, Tuple

from Core.discovery.peer_discovery import PeerDiscovery
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
        self.peer_id: Optional[str] = None  # Will be set in connect_core
        self.display_name: Optional[str] = None
        self.tcp_port = config.TCP_BASE_PORT

        self.data_manager: Optional[DataManager] = None
        self.peer_listener: Optional[PeerListener] = None
        self.peer_discovery: Optional[PeerDiscovery] = None
        self.peer_client = PeerClient()

        self._on_message_callback: Optional[Callable[[Message], None]] = None
        self._on_peer_callback: Optional[Callable[[PeerInfo], None]] = None
        self._on_temp_peer_callback: Optional[Callable[[PeerInfo], None]] = None
        self._on_temp_peer_removed_callback: Optional[Callable[[str], None]] = None  # peer_id
        self._on_friend_request_callback: Optional[Callable[[str, str], None]] = None  # peer_id, display_name
        self._on_friend_accepted_callback: Optional[Callable[[str], None]] = None  # peer_id
        self._on_friend_rejected_callback: Optional[Callable[[str], None]] = None  # peer_id
        self._lock = threading.RLock()
        
        self._peers: Dict[str, PeerInfo] = {}
        
        self.temp_discovered_peers: Dict[str, PeerInfo] = {}
        
        self._outgoing_requests: set[str] = set()  # peer_ids we sent FRIEND_REQUEST to
        self._incoming_requests: set[str] = set()  # peer_ids that sent us FRIEND_REQUEST
        self._friend_request_emitted: set[str] = set()  # peer_ids we already emitted friend_request callback for
        
        self._peer_send_failures: Dict[str, int] = {}  # peer_id -> failure count
        
        from Core.utils.network_mode import detect_network_mode
        self._network_mode = detect_network_mode()
        log.info("MessageRouter network mode: %s", self._network_mode)
        
        self._pending_friend_accepts: Dict[str, float] = {}
        
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
            actual_port = self.peer_listener.start(port=self.tcp_port)
            if actual_port != self.tcp_port:
                log.warning("TCP port changed from %s to %s (port was in use)", self.tcp_port, actual_port)
                self.tcp_port = actual_port
                profile = self.data_manager.load_profile()
                profile["tcp_port"] = actual_port
                self.data_manager.save_profile(profile)
            
            import time
            time.sleep(0.1)
            log.info("PeerListener started successfully on port %s", self.tcp_port)
        except Exception as e:
            log.error("Failed to start PeerListener: %s", e)
            raise RuntimeError(f"Failed to start TCP listener: {e}")

        if self.data_manager:
            self._peers = self.data_manager.load_peers()
            log.info("Loaded %s friends from peers.json", len(self._peers))
        
        self.peer_discovery = PeerDiscovery(
            peer_id=self.peer_id,
            display_name=self.display_name,
            tcp_port=self.tcp_port,
            data_manager=self.data_manager,
            on_peer_found=self._handle_peer_discovered,
        )
        self.peer_discovery.start()
        self._notify_existing_peers()
        
        import time
        time.sleep(0.2)
        self.status_broadcaster.broadcast_status("online")
        
        log.info("MessageRouter ready as %s (%s)", self.display_name, self.peer_id)

    def stop(self):
        self.status_broadcaster.broadcast_status("offline")
        
        if self.peer_discovery:
            self.peer_discovery.stop()
        if self.peer_listener:
            self.peer_listener.stop()

    def _handle_peer_discovered(self, peer_info: PeerInfo):
        
        if not peer_info.tcp_port or peer_info.tcp_port < 55000 or peer_info.tcp_port > 55199:
            log.warning("Discovered peer %s has invalid tcp_port %s, skipping", peer_info.peer_id, peer_info.tcp_port)
            return
        
        log.info("Discovered peer %s (%s) @ %s:%s", peer_info.display_name, peer_info.peer_id, peer_info.ip, peer_info.tcp_port)
        
        with self._lock:
            if peer_info.peer_id in self._peers:
                existing_peer = self._peers[peer_info.peer_id]
                updated = False
                if existing_peer.ip != peer_info.ip:
                    log.info("Updating friend %s IP from %s to %s (from discovery)", 
                            peer_info.peer_id, existing_peer.ip, peer_info.ip)
                    existing_peer.ip = peer_info.ip
                    updated = True
                if existing_peer.tcp_port != peer_info.tcp_port:
                    log.info("Updating friend %s port from %s to %s (from discovery)", 
                            peer_info.peer_id, existing_peer.tcp_port, peer_info.tcp_port)
                    existing_peer.tcp_port = peer_info.tcp_port
                    updated = True
                existing_peer.status = "online"
                existing_peer.touch("online")
                if updated and self.data_manager:
                    if existing_peer.tcp_port and 55000 <= existing_peer.tcp_port <= 55199:
                        self.data_manager.update_peer(existing_peer)
                    else:
                        log.warning("Cannot save peer %s: tcp_port is invalid (%s). Waiting for valid discovery.", 
                                   peer_info.peer_id, existing_peer.tcp_port)
                
                if peer_info.peer_id in self._pending_friend_accepts:
                    log.info("Discovery updated peer %s with valid tcp_port %s. Completing pending friend accept.", 
                            peer_info.peer_id, peer_info.tcp_port)
                    self.friend_request_manager.complete_pending_accept(peer_info.peer_id)
                
                return  # Already a friend - don't add to suggestions
            
            if peer_info.peer_id in self.temp_discovered_peers:
                existing = self.temp_discovered_peers[peer_info.peer_id]
                existing.ip = peer_info.ip
                existing.tcp_port = peer_info.tcp_port
                existing.touch("online")
                log.debug("Updated existing temp peer %s with fresh discovery info", peer_info.peer_id)
                return
            
            if peer_info.peer_id in self._outgoing_requests:
                log.debug("Ignoring discovered peer %s: already sent friend request", peer_info.peer_id)
                return  # Waiting for their response - don't add to suggestions
            
            if peer_info.peer_id in self._incoming_requests:
                log.debug("Ignoring discovered peer %s: already received friend request from them", peer_info.peer_id)
                return  # Waiting for our response - don't add to suggestions
            
            existing_temp = self.temp_discovered_peers.get(peer_info.peer_id)
            if existing_temp and existing_temp.tcp_port == 0:
                log.info("Updating temp peer %s with valid tcp_port %s from discovery", 
                        peer_info.peer_id, peer_info.tcp_port)
                existing_temp.tcp_port = peer_info.tcp_port
                existing_temp.ip = peer_info.ip
                existing_temp.touch("online")
                peer_info = existing_temp
            else:
                self.temp_discovered_peers[peer_info.peer_id] = peer_info
            
            if peer_info.peer_id in self._pending_friend_accepts:
                log.info("Discovery updated peer %s with valid tcp_port %s. Completing pending friend accept.", 
                        peer_info.peer_id, peer_info.tcp_port)
                self.friend_request_manager.complete_pending_accept(peer_info.peer_id)
                return
            
            if peer_info.peer_id in self._incoming_requests:
                if peer_info.peer_id not in self._friend_request_emitted:
                    log.info("Discovery updated peer %s with valid tcp_port %s. Emitting pending friend request callback.", 
                            peer_info.peer_id, peer_info.tcp_port)
                    self._friend_request_emitted.add(peer_info.peer_id)
                    if self._on_friend_request_callback:
                        try:
                            self._on_friend_request_callback(peer_info.peer_id, peer_info.display_name)
                        except Exception as e:
                            log.error("Error in _on_friend_request_callback for %s: %s", peer_info.peer_id, e, exc_info=True)
                else:
                    log.debug("Friend request callback already emitted for %s, skipping", peer_info.peer_id)
                return  # Don't add to suggestions - waiting for Accept/Reject
        
        if self._on_temp_peer_callback:
            try:
                self._on_temp_peer_callback(peer_info)
            except Exception as e:
                log.error("Error in _on_temp_peer_callback for %s: %s", peer_info.peer_id, e, exc_info=True)

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
        
        log.info(
            "Message from %s (%s): %s",
            message.sender_name,
            message.sender_id,
            message.content,
        )
        
        if self.data_manager:
            self.data_manager.append_message(message)
        
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
            log.warning("Cannot send message to %s: Peer not in friends list (not accepted)", to_peer_id)
            return False, None

        if not target.ip or not target.tcp_port:
            log.warning("Cannot send message to %s: Invalid IP (%s) or port (%s)", to_peer_id, target.ip, target.tcp_port)
            return False, None

        if target.ip == "0.0.0.0" or target.ip == "":
            log.warning("Cannot send message to %s: Invalid IP address", to_peer_id)
            return False, None

        if target.tcp_port == 0:
            log.warning("Cannot send message to %s: tcp_port is 0 (not discovered yet). Removing peer.", to_peer_id)
            with self._lock:
                if to_peer_id in self._peers:
                    del self._peers[to_peer_id]
            if self.data_manager:
                peers = self.data_manager.load_peers()
                peers.pop(to_peer_id, None)
                self.data_manager.save_peers(peers)
            return False, None
        
        if target.tcp_port < 55000 or target.tcp_port > 55199:
            log.warning("Cannot send message to %s: Port %s is outside valid range (55000-55199). "
                       "This may be a stale/ephemeral port. Removing peer.", to_peer_id, target.tcp_port)
            with self._lock:
                if to_peer_id in self._peers:
                    del self._peers[to_peer_id]
            if self.data_manager:
                peers = self.data_manager.load_peers()
                peers.pop(to_peer_id, None)
                self.data_manager.save_peers(peers)
            return False, None
        
        if target.status != "online":
            log.warning("Cannot send message to %s: Peer status is %s (not online)", to_peer_id, target.status)
            return False, None
        
        time_since_last_seen = time.time() - target.last_seen
        if time_since_last_seen > 300:  # 5 minutes
            log.warning("Cannot send message to %s: Peer last_seen is too old (%s seconds ago). "
                       "Marking as offline.", to_peer_id, int(time_since_last_seen))
            target.status = "offline"
            if self.data_manager:
                self.data_manager.update_peer(target)
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
                self.data_manager.append_message(message)
            log.info("Message sent successfully to %s (%s) at %s:%s", target.display_name, to_peer_id, target.ip, target.tcp_port)
        else:
            failures = self._peer_send_failures.get(to_peer_id, 0) + 1
            self._peer_send_failures[to_peer_id] = failures
            
            if failures >= 3:
                log.warning("Peer %s failed %s times, marking as offline", to_peer_id, failures)
                target.status = "offline"
                if self.data_manager:
                    self.data_manager.update_peer(target)
                self._peer_send_failures.pop(to_peer_id, None)
            
            log.warning("Failed to send message to %s (%s) at %s:%s - connection refused or peer offline", to_peer_id, target.display_name, target.ip, target.tcp_port)
        return success, message if success else None

    def get_known_peers(self) -> List[PeerInfo]:
        
        return self.peer_manager.get_known_peers()

    def get_message_history(self, peer_id: Optional[str] = None) -> List[Message]:
        if not self.data_manager:
            return []
        return self.data_manager.load_messages(peer_id=peer_id)

    def set_peer_callback(self, callback: Optional[Callable[[PeerInfo], None]]):
        self._on_peer_callback = callback

    def add_peer(self, peer_id: str) -> bool:
        
        return self.peer_manager.add_peer(peer_id)
    
    def get_temp_discovered_peers(self) -> List[PeerInfo]:
        
        return self.peer_manager.get_temp_discovered_peers()
    
    def set_temp_peer_callback(self, callback: Optional[Callable[[PeerInfo], None]]):
        
        self._on_temp_peer_callback = callback
    
    def set_temp_peer_removed_callback(self, callback: Optional[Callable[[str], None]]):
        
        self._on_temp_peer_removed_callback = callback
    
    def remove_temp_peer(self, peer_id: str) -> bool:
        
        return self.peer_manager.remove_temp_peer(peer_id)
    
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

    def cleanup_offline_peers(self, max_offline_time: float = 600.0) -> int:
        
        return self.peer_manager.cleanup_offline_peers(max_offline_time)
    
    def _get_local_ip_for_sync(self) -> str:
        
        try:
            from Core.utils.network_mode import get_local_ip
            return get_local_ip(self._network_mode)
        except Exception:
            return "127.0.0.1"

    def _notify_existing_peers(self):
        
        self.peer_manager.notify_existing_peers()
