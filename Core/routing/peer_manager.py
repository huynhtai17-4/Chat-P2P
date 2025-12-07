import logging
import time
from typing import Callable, Dict, List, Optional

from Core.models.peer_info import PeerInfo

log = logging.getLogger(__name__)

class PeerManager:

    def __init__(self, router):
        self.router = router
    
    def add_peer(self, peer_id: str) -> bool:
        
        with self.router._lock:
            if peer_id in self.router._peers:
                log.info("Peer %s already in friends list", peer_id)
                return True
            
            if peer_id not in self.router.temp_discovered_peers:
                log.warning("Peer %s not found in discovered peers", peer_id)
                return False
            
            peer_info = self.router.temp_discovered_peers[peer_id]
            self.router._peers[peer_id] = peer_info
            del self.router.temp_discovered_peers[peer_id]
            self.router._outgoing_requests.discard(peer_id)
            self.router._incoming_requests.discard(peer_id)
            peer_info_copy = peer_info
        
        if not peer_info_copy.tcp_port or peer_info_copy.tcp_port < 55000 or peer_info_copy.tcp_port > 55199:
            log.warning("Cannot add peer %s: invalid tcp_port %s (must be 55000-55199).", 
                       peer_id, peer_info_copy.tcp_port)
            return False
        
        if self.router.data_manager:
            self.router.data_manager.update_peer(peer_info_copy)
            log.info("Added peer %s (%s) to known peers", peer_info_copy.display_name, peer_id)
        
        if self.router._on_temp_peer_removed_callback:
            self.router._on_temp_peer_removed_callback(peer_id)
        
        if self.router._on_peer_callback:
            try:
                self.router._on_peer_callback(peer_info_copy)
            except Exception as e:
                log.error("Error in _on_peer_callback for added peer %s: %s", peer_id, e, exc_info=True)
        
        return True
    
    def get_known_peers(self) -> List[PeerInfo]:
        
        with self.router._lock:
            now = time.time()
            return sorted(
                list(self.router._peers.values()),
                key=lambda peer: now - peer.last_seen,
            )
    
    def get_temp_discovered_peers(self) -> List[PeerInfo]:
        
        with self.router._lock:
            temp_only = [
                peer for peer_id, peer in self.router.temp_discovered_peers.items()
                if peer_id not in self.router._peers
                and peer_id not in self.router._outgoing_requests
                and peer_id not in self.router._incoming_requests
            ]
            return temp_only
    
    def remove_temp_peer(self, peer_id: str) -> bool:
        
        with self.router._lock:
            if peer_id in self.router.temp_discovered_peers:
                del self.router.temp_discovered_peers[peer_id]
                log.info("Removed peer %s from suggestions", peer_id)
                if self.router._on_temp_peer_removed_callback:
                    try:
                        self.router._on_temp_peer_removed_callback(peer_id)
                    except Exception as e:
                        log.error("Error in _on_temp_peer_removed_callback for %s: %s", peer_id, e, exc_info=True)
                return True
        return False
    
    def cleanup_offline_peers(self, max_offline_time: float = 600.0) -> int:
        
        from Core.utils import config
        offline_timeout = getattr(config, 'OFFLINE_PEER_CLEANUP_TIMEOUT', max_offline_time)
        
        with self.router._lock:
            peers_to_remove = []
            now = time.time()
            for peer_id, peer in self.router._peers.items():
                if peer.status == "offline" and (now - peer.last_seen > offline_timeout):
                    peers_to_remove.append(peer_id)
            
            for peer_id in peers_to_remove:
                log.info("Removing offline peer %s from friends list (offline for > %s seconds)", peer_id, offline_timeout)
                del self.router._peers[peer_id]
                if self.router.data_manager:
                    self.router.data_manager.remove_peer(peer_id)
                if self.router._on_peer_callback:
                    try:
                        removed_peer = PeerInfo(peer_id=peer_id, display_name="", ip="", tcp_port=0, last_seen=0, status="removed")
                        self.router._on_peer_callback(removed_peer)
                    except Exception as e:
                        log.error("Error in _on_peer_callback for removed peer %s: %s", peer_id, e, exc_info=True)
        
        return len(peers_to_remove)
    
    def notify_existing_peers(self):
        
        if not self.router._on_peer_callback:
            return
        with self.router._lock:
            for peer in self.router._peers.values():
                try:
                    self.router._on_peer_callback(peer)
                except Exception as e:
                    log.error("Error in _on_peer_callback for peer %s: %s", peer.peer_id, e, exc_info=True)
