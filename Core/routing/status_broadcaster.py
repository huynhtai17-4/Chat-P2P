import logging
from typing import List

from Core.models.message import Message
from Core.models.peer_info import PeerInfo

log = logging.getLogger(__name__)

class StatusBroadcaster:

    def __init__(self, router):
        self.router = router
    
    def broadcast_status(self, status: str):
        
        if not self.router.peer_listener or not self.router.peer_listener._thread or not self.router.peer_listener._thread.is_alive():
            log.debug("PeerListener not running, skipping status broadcast")
            return
        
        if status not in ("online", "offline"):
            log.warning("Invalid status for broadcast: %s", status)
            return
        
        msg_type = "ONLINE" if status == "online" else "OFFLINE"
        
        with self.router._lock:
            friends = list(self.router._peers.values())
        
        sent_count = 0
        for peer in friends:
            if not peer.ip or not peer.tcp_port or peer.tcp_port == 0:
                log.debug("Skipping status broadcast to %s: invalid IP/port", peer.peer_id)
                continue
            
            try:
                if status == "online":
                    message = Message.create_online_status(
                        sender_id=self.router.peer_id,
                        sender_name=self.router.display_name or "Unknown",
                        receiver_id=peer.peer_id
                    )
                else:
                    message = Message.create_offline_status(
                        sender_id=self.router.peer_id,
                        sender_name=self.router.display_name or "Unknown",
                        receiver_id=peer.peer_id
                    )
                
                success = self.router.peer_client.send(peer.ip, peer.tcp_port, message)
                if success:
                    sent_count += 1
                    log.debug("Sent %s status to %s (%s)", status, peer.display_name, peer.peer_id)
                else:
                    log.debug("Failed to send %s status to %s (%s)", status, peer.display_name, peer.peer_id)
            except Exception as e:
                log.warning("Error sending %s status to %s: %s", status, peer.peer_id, e)
        
        log.info("Broadcasted %s status to %s/%s friends", status, sent_count, len(friends))
