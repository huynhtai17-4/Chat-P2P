import logging
import time
from typing import Optional

from Core.models.message import Message
from Core.models.peer_info import PeerInfo

log = logging.getLogger(__name__)

class FriendRequestManager:

    def __init__(self, router):
        self.router = router
    
    def send_friend_request(self, peer_id: str) -> bool:
        
        if not self.router.peer_listener or not self.router.peer_listener._thread or not self.router.peer_listener._thread.is_alive():
            log.error("PeerListener not running. Cannot send friend request.")
            return False
        
        with self.router._lock:
            peer_info = self.router.temp_discovered_peers.get(peer_id)
            if not peer_info:
                log.warning("Peer %s not found in discovered peers", peer_id)
                return False
            
            if not peer_info.ip or not peer_info.tcp_port:
                log.warning("Cannot send friend request to %s: Invalid IP (%s) or port (%s)", 
                           peer_id, peer_info.ip, peer_info.tcp_port)
                return False
            
            if peer_info.ip == "0.0.0.0" or peer_info.ip == "":
                log.warning("Cannot send friend request to %s: Invalid IP address", peer_id)
                return False
            
            if peer_info.tcp_port <= 0 or peer_info.tcp_port > 65535:
                log.warning("Cannot send friend request to %s: Invalid port %s", peer_id, peer_info.tcp_port)
                return False
            
            if peer_info.tcp_port == 0:
                log.warning("Cannot send friend request to %s: tcp_port is 0 (not discovered yet)", peer_id)
                return False
            
            if peer_info.tcp_port < 55000 or peer_info.tcp_port > 55199:
                log.warning("Cannot send friend request to %s: Port %s is outside valid range (55000-55199)", 
                           peer_id, peer_info.tcp_port)
                return False
            
            self.router._outgoing_requests.add(peer_id)
        
        message = Message.create_friend_request(
            sender_id=self.router.peer_id,
            sender_name=self.router.display_name or "Unknown",
            receiver_id=peer_id,
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
            if peer_id in self.router._peers:
                log.info("Peer %s already in friends list", peer_id)
                peer_info = self.router._peers[peer_id]
            else:
                peer_info = self.router.temp_discovered_peers.get(peer_id)
                if not peer_info:
                    log.info("Peer %s not found in discovered peers. Marking as pending accept.", peer_id)
                    self.router._pending_friend_accepts[peer_id] = time.time()
                    return False
                
                self.router._peers[peer_id] = peer_info
                
                if peer_id in self.router.temp_discovered_peers:
                    del self.router.temp_discovered_peers[peer_id]
                self.router._outgoing_requests.discard(peer_id)
                self.router._incoming_requests.discard(peer_id)
            
            if not peer_info.ip or not peer_info.tcp_port:
                log.warning("Cannot send friend accept to %s: Invalid IP (%s) or port (%s)", 
                           peer_id, peer_info.ip, peer_info.tcp_port)
                return False
            
            if peer_info.ip == "0.0.0.0" or peer_info.ip == "":
                log.warning("Cannot send friend accept to %s: Invalid IP address", peer_id)
                return False
            
            if peer_info.tcp_port <= 0 or peer_info.tcp_port > 65535:
                log.warning("Cannot send friend accept to %s: Invalid port %s", peer_id, peer_info.tcp_port)
                return False
            
            if peer_info.tcp_port == 0:
                log.info("Peer %s has tcp_port=0. Marking as pending accept.", peer_id)
                self.router._pending_friend_accepts[peer_id] = time.time()
                return False
            
            if peer_info.tcp_port < 55000 or peer_info.tcp_port > 55199:
                log.warning("Cannot send friend accept to %s: Port %s is outside valid range (55000-55199).", 
                           peer_id, peer_info.tcp_port)
                return False
        
        if self.router.data_manager:
            if peer_info.tcp_port and 55000 <= peer_info.tcp_port <= 55199:
                self.router.data_manager.update_peer(peer_info)
                log.info("Saved peer %s (%s) to friends list", peer_info.display_name, peer_id)
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
                peers[peer_id] = temp_peer
                self.router.data_manager.save_peers(peers)
        
        if self.router._on_temp_peer_removed_callback:
            try:
                self.router._on_temp_peer_removed_callback(peer_id)
            except Exception as e:
                log.error("Error in _on_temp_peer_removed_callback for %s: %s", peer_id, e, exc_info=True)
        
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
            
            sync_message = Message.create_friend_sync(
                sender_id=self.router.peer_id,
                sender_name=self.router.display_name or "Unknown",
                receiver_id=peer_id,
                peer_ip=self.router._get_local_ip_for_sync(),
                peer_tcp_port=self.router.tcp_port,
            )
            try:
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
        
        peer_info = self.router.temp_discovered_peers.get(peer_id)
        if not peer_info:
            log.warning("Peer %s not found in discovered peers", peer_id)
            return False
        
        if not peer_info.ip or not peer_info.tcp_port:
            log.warning("Cannot send friend reject to %s: Invalid IP (%s) or port (%s)", 
                       peer_id, peer_info.ip, peer_info.tcp_port)
            return False
        
        if peer_info.ip == "0.0.0.0" or peer_info.ip == "":
            log.warning("Cannot send friend reject to %s: Invalid IP address", peer_id)
            return False
        
        if peer_info.tcp_port <= 0 or peer_info.tcp_port > 65535:
            log.warning("Cannot send friend reject to %s: Invalid port %s", peer_id, peer_info.tcp_port)
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
        else:
            log.warning("Failed to send friend reject to %s (%s:%s)", peer_id, peer_info.ip, peer_info.tcp_port)
        
        return success
    
    def complete_pending_accept(self, peer_id: str):
        
        if peer_id not in self.router._pending_friend_accepts:
            return
        
        del self.router._pending_friend_accepts[peer_id]
        
        peer_info = self.router.temp_discovered_peers.get(peer_id)
        if not peer_info:
            log.warning("Cannot complete pending accept for %s: peer not in temp_discovered_peers", peer_id)
            return
        
        if not peer_info.tcp_port or peer_info.tcp_port < 55000 or peer_info.tcp_port > 55199:
            log.warning("Cannot complete pending accept for %s: tcp_port still invalid (%s)", 
                       peer_id, peer_info.tcp_port)
            return
        
        log.info("Completing pending friend accept for %s with tcp_port %s", peer_id, peer_info.tcp_port)
        
        with self.router._lock:
            self.router._peers[peer_id] = peer_info
            if peer_id in self.router.temp_discovered_peers:
                del self.router.temp_discovered_peers[peer_id]
            self.router._outgoing_requests.discard(peer_id)
            self.router._incoming_requests.discard(peer_id)
        
        if self.router.data_manager:
            if peer_info.tcp_port and 55000 <= peer_info.tcp_port <= 55199:
                self.router.data_manager.update_peer(peer_info)
                log.info("Saved peer %s (%s) to friends list", peer_info.display_name, peer_id)
        
        if self.router._on_temp_peer_removed_callback:
            try:
                self.router._on_temp_peer_removed_callback(peer_id)
            except Exception as e:
                log.error("Error in _on_temp_peer_removed_callback for %s: %s", peer_id, e, exc_info=True)
        
        if self.router._on_peer_callback:
            try:
                self.router._on_peer_callback(peer_info)
            except Exception as e:
                log.error("Error in _on_peer_callback for %s: %s", peer_id, e, exc_info=True)
        
        if self.router._on_friend_accepted_callback:
            try:
                self.router._on_friend_accepted_callback(peer_id)
            except Exception as e:
                log.error("Error in _on_friend_accepted_callback for %s: %s", peer_id, e, exc_info=True)
        
        message = Message.create_friend_accept(
            sender_id=self.router.peer_id,
            sender_name=self.router.display_name or "Unknown",
            receiver_id=peer_id,
        )
        
        log.info("Sending friend accept to %s (%s:%s)", peer_info.display_name, peer_info.ip, peer_info.tcp_port)
        success = self.router.peer_client.send(peer_info.ip, peer_info.tcp_port, message)
        if success:
            log.info("Friend accept sent to %s (%s)", peer_info.display_name, peer_id)
        else:
            log.warning("Failed to send friend accept to %s (%s:%s)", peer_id, peer_info.ip, peer_info.tcp_port)
