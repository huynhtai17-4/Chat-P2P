import logging
import time
from typing import Callable, Dict, List, Optional

from Core.models.peer_info import PeerInfo

log = logging.getLogger(__name__)

class PeerManager:

    def __init__(self, router):
        self.router = router
    
    def add_peer(self, peer_id: str) -> bool:
        # Legacy method - no longer used with Add Friend by IP
        # Kept for compatibility
        with self.router._lock:
            if peer_id in self.router._peers:
                log.info("Peer %s already in friends list", peer_id)
                return True
        log.warning("add_peer called but no discovery - use add_peer_by_ip instead")
        return False
    
    def get_known_peers(self) -> List[PeerInfo]:
        
        with self.router._lock:
            return list(self.router._peers.values())
    
    def get_temp_discovered_peers(self) -> List[PeerInfo]:
        # Discovery removed - return empty list
        return []
    
    def remove_temp_peer(self, peer_id: str) -> bool:
        # Discovery removed - no temp peers to remove
        return False
    
    def cleanup_offline_peers(self, max_offline_time: float = 600.0) -> int:
        # Disabled offline cleanup (no heartbeat/last_seen based removal)
        return 0
    
    def notify_existing_peers(self):
        
        if not self.router._on_peer_callback:
            return
        with self.router._lock:
            for peer in self.router._peers.values():
                try:
                    self.router._on_peer_callback(peer)
                except Exception as e:
                    log.error("Error in _on_peer_callback for peer %s: %s", peer.peer_id, e, exc_info=True)
