import logging
import time
from typing import Callable, Dict, Optional

from Core.models.message import Message
from Core.models.peer_info import PeerInfo

log = logging.getLogger(__name__)

class MessageHandlers:

    def __init__(self, router):
        self.router = router
    
    def handle_friend_request(self, message: Message, sender_ip: str = ""):
        
        log.info("Friend request from %s (%s)", message.sender_name, message.sender_id)
        
        with self.router._lock:
            if message.sender_id in self.router._peers:
                log.debug("Ignoring friend request from %s: already a friend", message.sender_id)
                return
            
            if message.sender_id in self.router._incoming_requests:
                log.debug("Ignoring duplicate friend request from %s", message.sender_id)
                return
            
            self.router._incoming_requests.add(message.sender_id)
        
        peer_info = self.router.temp_discovered_peers.get(message.sender_id)
        if not peer_info:
            log.info("Friend request from %s (%s) but peer not discovered yet.", 
                    message.sender_name, message.sender_id)
            with self.router._lock:
                self.router.temp_discovered_peers[message.sender_id] = PeerInfo(
                    peer_id=message.sender_id,
                    display_name=message.sender_name,
                    ip=sender_ip if sender_ip else "127.0.0.1",
                    tcp_port=0,
                    last_seen=message.timestamp,
                    status="offline",
                )
            return
        else:
            if sender_ip:
                peer_info.ip = sender_ip
            peer_info.touch()
            log.debug("Updated peer %s IP to %s", message.sender_id, sender_ip)
        
        if message.sender_id not in self.router._friend_request_emitted:
            self.router._friend_request_emitted.add(message.sender_id)
            if self.router._on_friend_request_callback:
                try:
                    self.router._on_friend_request_callback(message.sender_id, message.sender_name)
                except Exception as e:
                    log.error("Error in _on_friend_request_callback for %s: %s", message.sender_id, e, exc_info=True)
    
    def handle_friend_accept(self, message: Message, sender_ip: str = ""):
        
        log.info("Friend accepted by %s (%s)", message.sender_name, message.sender_id)
        
        with self.router._lock:
            if message.sender_id in self.router._peers:
                existing_peer = self.router._peers[message.sender_id]
                existing_peer.touch()
                if sender_ip:
                    existing_peer.ip = sender_ip
                if self.router.data_manager:
                    self.router.data_manager.update_peer(existing_peer)
                if self.router._on_peer_callback:
                    try:
                        self.router._on_peer_callback(existing_peer)
                    except Exception as e:
                        log.error("Error in _on_peer_callback for existing friend %s: %s", message.sender_id, e, exc_info=True)
                if self.router._on_friend_accepted_callback:
                    try:
                        self.router._on_friend_accepted_callback(message.sender_id)
                    except Exception as e:
                        log.error("Error in _on_friend_accepted_callback for %s: %s", message.sender_id, e, exc_info=True)
                return
            
            peer_info = self.router.temp_discovered_peers.get(message.sender_id)
            
            if not peer_info:
                log.info("FRIEND_ACCEPT from %s (%s) but peer not discovered yet.", 
                        message.sender_name, message.sender_id)
                peer_info = PeerInfo(
                    peer_id=message.sender_id,
                    display_name=message.sender_name,
                    ip=sender_ip if sender_ip else "127.0.0.1",
                    tcp_port=0,
                    last_seen=message.timestamp,
                    status="offline",
                )
                self.router.temp_discovered_peers[message.sender_id] = peer_info
                self.router._pending_friend_accepts[message.sender_id] = time.time()
                return
            
            if sender_ip:
                peer_info.ip = sender_ip
            peer_info.touch()
            
            self.router._peers[message.sender_id] = peer_info
            
            if message.sender_id in self.router.temp_discovered_peers:
                del self.router.temp_discovered_peers[message.sender_id]
            
            self.router._outgoing_requests.discard(message.sender_id)
            self.router._incoming_requests.discard(message.sender_id)
            self.router._friend_request_emitted.discard(message.sender_id)
        
        if self.router.data_manager:
            if peer_info.tcp_port and 55000 <= peer_info.tcp_port <= 55199:
                self.router.data_manager.update_peer(peer_info)
                log.info("Saved peer %s (%s) to friends list", peer_info.display_name, message.sender_id)
            else:
                temp_peer = PeerInfo(
                    peer_id=peer_info.peer_id,
                    display_name=peer_info.display_name,
                    ip=peer_info.ip,
                    tcp_port=55000,
                    last_seen=peer_info.last_seen,
                    status=peer_info.status,
                )
                peers = self.router.data_manager.load_peers()
                peers[message.sender_id] = temp_peer
                self.router.data_manager.save_peers(peers)
        
        if self.router._on_temp_peer_removed_callback:
            try:
                self.router._on_temp_peer_removed_callback(message.sender_id)
            except Exception as e:
                log.error("Error in _on_temp_peer_removed_callback for %s: %s", message.sender_id, e, exc_info=True)
        
        if self.router._on_peer_callback:
            try:
                self.router._on_peer_callback(peer_info)
            except Exception as e:
                log.error("Error in _on_peer_callback for new friend %s: %s", message.sender_id, e, exc_info=True)
        
        if self.router._on_friend_accepted_callback:
            try:
                self.router._on_friend_accepted_callback(message.sender_id)
            except Exception as e:
                log.error("Error in _on_friend_accepted_callback for %s: %s", message.sender_id, e, exc_info=True)
        
        if peer_info.ip and peer_info.tcp_port and 55000 <= peer_info.tcp_port <= 55199:
            sync_message = Message.create_friend_sync(
                sender_id=self.router.peer_id,
                sender_name=self.router.display_name or "Unknown",
                receiver_id=message.sender_id,
                peer_ip=self.router._get_local_ip_for_sync(),
                peer_tcp_port=self.router.tcp_port,
            )
            try:
                self.router.peer_client.send(peer_info.ip, peer_info.tcp_port, sync_message)
                log.info("Sent FRIEND_SYNC to %s", message.sender_id)
            except Exception as e:
                log.warning("Failed to send FRIEND_SYNC to %s: %s", message.sender_id, e)
    
    def handle_friend_sync(self, message: Message, sender_ip: str = ""):
        
        log.info("FRIEND_SYNC received from %s (%s)", message.sender_name, message.sender_id)
        
        try:
            import json
            sync_data = json.loads(message.content)
            peer_ip = sync_data.get("ip", sender_ip if sender_ip else "127.0.0.1")
            peer_tcp_port = int(sync_data.get("tcp_port", 0))
            
            if peer_tcp_port < 55000 or peer_tcp_port > 55199:
                log.warning("FRIEND_SYNC from %s has invalid tcp_port %s", message.sender_id, peer_tcp_port)
                return
            
            with self.router._lock:
                if message.sender_id in self.router._peers:
                    existing_peer = self.router._peers[message.sender_id]
                    existing_peer.ip = peer_ip
                    existing_peer.tcp_port = peer_tcp_port
                    existing_peer.display_name = message.sender_name
                    existing_peer.touch()
                    peer_info = existing_peer
                else:
                    peer_info = PeerInfo(
                        peer_id=message.sender_id,
                        display_name=message.sender_name,
                        ip=peer_ip,
                        tcp_port=peer_tcp_port,
                        last_seen=message.timestamp,
                        status="offline",
                    )
                    self.router._peers[message.sender_id] = peer_info
                
                if message.sender_id in self.router.temp_discovered_peers:
                    del self.router.temp_discovered_peers[message.sender_id]
                self.router._outgoing_requests.discard(message.sender_id)
                self.router._incoming_requests.discard(message.sender_id)
            
            if self.router.data_manager:
                self.router.data_manager.update_peer(peer_info)
                log.info("Saved peer %s (%s) from FRIEND_SYNC", peer_info.display_name, message.sender_id)
            
            if self.router._on_peer_callback:
                try:
                    self.router._on_peer_callback(peer_info)
                except Exception as e:
                    log.error("Error in _on_peer_callback for FRIEND_SYNC %s: %s", message.sender_id, e, exc_info=True)
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            log.error("Failed to parse FRIEND_SYNC from %s: %s", message.sender_id, e)
    
    def handle_status_message(self, message: Message, sender_ip: str = ""):
        
        msg_type = message.msg_type
        log.info("Received %s status from %s (%s)", msg_type, message.sender_name, message.sender_id)
        
        with self.router._lock:
            if message.sender_id not in self.router._peers:
                log.debug("Ignoring %s status from %s: not a friend", msg_type, message.sender_id)
                return
            
            peer = self.router._peers[message.sender_id]
            new_status = "online" if msg_type == "ONLINE" else "offline"
            old_status = peer.status
            
            peer.status = new_status
            peer.touch(new_status)
            
            if sender_ip:
                peer.ip = sender_ip
            
            log.info("Updated peer %s (%s) status: %s -> %s", 
                    peer.display_name, message.sender_id, old_status, new_status)
            if self.router._on_peer_callback:
                try:
                    self.router._on_peer_callback(peer)
                except Exception as e:
                    log.error("Error in _on_peer_callback for status update %s: %s", message.sender_id, e, exc_info=True)
    
    def handle_friend_reject(self, message: Message):
        
        log.info("Friend rejected by %s (%s)", message.sender_name, message.sender_id)
        with self.router._lock:
            self.router._outgoing_requests.discard(message.sender_id)
        if self.router._on_friend_rejected_callback:
            try:
                self.router._on_friend_rejected_callback(message.sender_id)
            except Exception as e:
                log.error("Error in _on_friend_rejected_callback for %s: %s", message.sender_id, e, exc_info=True)
