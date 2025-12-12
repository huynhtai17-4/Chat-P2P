import logging
import time
from typing import Callable, Dict, List, Optional

from Core.models.peer_info import PeerInfo

log = logging.getLogger(__name__)

class PeerManager:

    def __init__(self, router):
        self.router = router
    
    def get_known_peers(self) -> List[PeerInfo]:
        
        with self.router._lock:
            return list(self.router._peers.values())
    
    def notify_existing_peers(self):
        
        if not self.router._on_peer_callback:
            return
        with self.router._lock:
            for peer in self.router._peers.values():
                try:
                    self.router._on_peer_callback(peer)
                except Exception as e:
                    log.error("Error in _on_peer_callback for peer %s: %s", peer.peer_id, e, exc_info=True)
