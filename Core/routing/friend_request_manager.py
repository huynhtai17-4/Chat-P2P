import logging
from typing import Optional

from Core.models.message import Message

log = logging.getLogger(__name__)

class FriendRequestManager:

    def __init__(self, router):
        self.router = router
    
    def send_friend_request(self, peer_id: str) -> bool:
        if not self.router.peer_listener or not self.router.peer_listener._thread or not self.router.peer_listener._thread.is_alive():
            log.error("PeerListener not running. Cannot send friend request.")
            return False
        
        with self.router._lock:
            peer_info = self.router._peers.get(peer_id)
            if not peer_info:
                log.warning("Cannot send friend request to %s: Peer not in friends list. Add by IP first.", peer_id)
                return False
            
            if not peer_info.ip or not peer_info.tcp_port:
                log.warning("Cannot send friend request to %s: Invalid IP (%s) or port (%s)", 
                           peer_id, peer_info.ip, peer_info.tcp_port)
                return False
            
            if peer_info.ip == "0.0.0.0" or peer_info.ip == "":
                log.warning("Cannot send friend request to %s: Invalid IP address", peer_id)
                return False
            
            if peer_info.tcp_port < 1 or peer_info.tcp_port > 65535:
                log.warning("Cannot send friend request to %s: Port %s is outside valid range (1-65535)", 
                           peer_id, peer_info.tcp_port)
                return False
            
            self.router._outgoing_requests.add(peer_id)
        
        message = Message.create_friend_request(
            sender_id=self.router.peer_id,
            sender_name=self.router.display_name or "Unknown",
            receiver_id=peer_id,
            tcp_port=self.router.tcp_port,
        )
        
        log.info("Sending friend request to %s (%s:%s)", peer_info.display_name, peer_info.ip, peer_info.tcp_port)
        success = self.router.peer_client.send(peer_info.ip, peer_info.tcp_port, message)
        if success:
            log.info("Friend request sent to %s (%s)", peer_info.display_name, peer_id)
        else:
            with self.router._lock:
                self.router._outgoing_requests.discard(peer_id)
            log.warning("Failed to send friend request to %s (%s:%s)", peer_id, peer_info.ip, peer_info.tcp_port)
        
        return success
    
    def send_friend_accept(self, peer_id: str) -> bool:
        if not self.router.peer_listener or not self.router.peer_listener._thread or not self.router.peer_listener._thread.is_alive():
            log.error("PeerListener not running. Cannot send friend accept.")
            return False
        
        with self.router._lock:
            peer_info = self.router._peers.get(peer_id)
            if not peer_info:
                log.warning("Cannot send friend accept to %s: Peer not in friends list", peer_id)
                return False
            
            if not peer_info.ip or not peer_info.tcp_port:
                log.warning("Cannot send friend accept to %s: Invalid IP (%s) or port (%s)", 
                           peer_id, peer_info.ip, peer_info.tcp_port)
                return False
            
            if peer_info.ip == "0.0.0.0" or peer_info.ip == "":
                log.warning("Cannot send friend accept to %s: Invalid IP address", peer_id)
                return False
            
            if peer_info.tcp_port < 55000 or peer_info.tcp_port > 55199:
                log.warning("Cannot send friend accept to %s: Port %s is outside valid range (55000-55199)", 
                           peer_id, peer_info.tcp_port)
                return False
            
            self.router._outgoing_requests.discard(peer_id)
            self.router._incoming_requests.discard(peer_id)
        
        if self.router.data_manager:
            self.router.data_manager.update_peer(peer_info)
            log.info("Updated peer %s (%s) after friend accept", peer_info.display_name, peer_id)
        
        if self.router._on_peer_callback:
            try:
                self.router._on_peer_callback(peer_info)
            except Exception as e:
                log.error("Error in _on_peer_callback for accepted friend %s: %s", peer_id, e, exc_info=True)
        
        message = Message.create_friend_accept(
            sender_id=self.router.peer_id,
            sender_name=self.router.display_name or "Unknown",
            receiver_id=peer_id,
        )
        
        log.info("Sending friend accept to %s (%s:%s)", peer_info.display_name, peer_info.ip, peer_info.tcp_port)
        success = self.router.peer_client.send(peer_info.ip, peer_info.tcp_port, message)
        if success:
            log.info("Friend accept sent to %s (%s)", peer_info.display_name, peer_id)
            
            try:
                sync_message = Message.create_friend_sync(
                    sender_id=self.router.peer_id,
                    sender_name=self.router.display_name or "Unknown",
                    receiver_id=peer_id,
                    peer_ip=self.router._get_local_ip_for_sync(),
                    peer_tcp_port=self.router.tcp_port,
                )
                self.router.peer_client.send(peer_info.ip, peer_info.tcp_port, sync_message)
                log.info("Sent FRIEND_SYNC to %s", peer_id)
            except Exception as e:
                log.warning("Failed to send FRIEND_SYNC to %s: %s", peer_id, e)
        else:
            log.warning("Failed to send friend accept to %s (%s:%s)", peer_id, peer_info.ip, peer_info.tcp_port)
        
        return success
    
    def send_friend_reject(self, peer_id: str) -> bool:
        if not self.router.peer_listener or not self.router.peer_listener._thread or not self.router.peer_listener._thread.is_alive():
            log.error("PeerListener not running. Cannot send friend reject.")
            return False
        
        with self.router._lock:
            peer_info = self.router._peers.get(peer_id)
            if not peer_info:
                log.warning("Cannot send friend reject to %s: Peer not in friends list", peer_id)
                return False
            
            if not peer_info.ip or not peer_info.tcp_port:
                log.warning("Cannot send friend reject to %s: Invalid IP (%s) or port (%s)", 
                           peer_id, peer_info.ip, peer_info.tcp_port)
                return False
            
            if peer_info.ip == "0.0.0.0" or peer_info.ip == "":
                log.warning("Cannot send friend reject to %s: Invalid IP address", peer_id)
                return False
            
            if peer_info.tcp_port < 55000 or peer_info.tcp_port > 55199:
                log.warning("Cannot send friend reject to %s: Port %s is outside valid range (55000-55199)", 
                           peer_id, peer_info.tcp_port)
                return False
        
        message = Message.create_friend_reject(
            sender_id=self.router.peer_id,
            sender_name=self.router.display_name or "Unknown",
            receiver_id=peer_id,
        )
        
        log.info("Sending friend reject to %s (%s:%s)", peer_info.display_name, peer_info.ip, peer_info.tcp_port)
        success = self.router.peer_client.send(peer_info.ip, peer_info.tcp_port, message)
        if success:
            log.info("Friend reject sent to %s (%s)", peer_info.display_name, peer_id)
            with self.router._lock:
                self.router._outgoing_requests.discard(peer_id)
        else:
            log.warning("Failed to send friend reject to %s (%s:%s)", peer_id, peer_info.ip, peer_info.tcp_port)
        
        return success
