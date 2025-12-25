import base64
import logging
from pathlib import Path
from typing import List

from Core.models.message import Message
from Core.models.peer_info import PeerInfo

log = logging.getLogger(__name__)

class StatusBroadcaster:

    def __init__(self, router):
        self.router = router
    
    def _check_network_connectivity(self, peer_ip: str, peer_name: str):
        try:
            # Get local IP
            local_ip = getattr(self.router, 'local_ip', None)
            if not local_ip:
                return
            
            # Extract subnets (first 3 octets)
            local_parts = local_ip.split('.')
            peer_parts = peer_ip.split('.')
            
            if len(local_parts) >= 3 and len(peer_parts) >= 3:
                local_subnet = f"{local_parts[0]}.{local_parts[1]}.{local_parts[2]}"
                peer_subnet = f"{peer_parts[0]}.{peer_parts[1]}.{peer_parts[2]}"
                
                if local_subnet != peer_subnet:
                    log.warning("NETWORK WARNING: Peer '%s' is on different subnet!", peer_name)
                    log.warning("Local IP: %s (subnet: %s.x)", local_ip, local_subnet)
                    log.warning("Peer IP:  %s (subnet: %s.x)", peer_ip, peer_subnet)
        except Exception as e:
            log.debug("Network connectivity check failed: %s", e)
    
    def broadcast_status(self, status: str):
        
        if not self.router.peer_listener or not self.router.peer_listener._thread or not self.router.peer_listener._thread.is_alive():
            log.warning("[STATUS] PeerListener not running, skipping status broadcast")
            return
        
        if status not in ("online", "offline"):
            log.warning("Invalid status for broadcast: %s", status)
            return
        
        msg_type = "ONLINE" if status == "online" else "OFFLINE"
        
        with self.router._lock:
            friends = list(self.router._peers.values())
        
        log.info("=" * 60)
        log.info("Broadcasting %s to %d friend(s)", status.upper(), len(friends))
        log.info("=" * 60)
        
        sent_count = 0
        failed_peers = []
        
        for peer in friends:
            if not peer.ip or not peer.tcp_port or peer.tcp_port == 0:
                log.warning("Skipping %s: invalid IP=%s or port=%s", 
                          peer.display_name, peer.ip, peer.tcp_port)
                failed_peers.append(f"{peer.display_name} (invalid address)")
                continue
            
            if status == "online":
                self._check_network_connectivity(peer.ip, peer.display_name)
            
            try:
                if status == "online":
                    avatar_base64 = None
                    avatar_path = getattr(self.router, 'avatar_path', None)
                    if avatar_path:
                        try:
                            avatar_file = Path(avatar_path)
                            if avatar_file.exists():
                                with open(avatar_file, 'rb') as f:
                                    avatar_base64 = base64.b64encode(f.read()).decode('utf-8')
                        except Exception as e:
                            log.warning("Failed to read avatar file %s: %s", avatar_path, e)
                    
                    message = Message.create_online_status(
                        sender_id=self.router.peer_id,
                        sender_name=self.router.display_name or "Unknown",
                        receiver_id=peer.peer_id,
                        avatar_base64=avatar_base64
                    )
                else:
                    message = Message.create_offline_status(
                        sender_id=self.router.peer_id,
                        sender_name=self.router.display_name or "Unknown",
                        receiver_id=peer.peer_id
                    )
                
                timeout = 2.0 if status == "offline" else 3.0
                log.debug("→ Sending %s to %s (%s:%d)...", status.upper(), peer.display_name, peer.ip, peer.tcp_port)
                success = self.router.peer_client.send(peer.ip, peer.tcp_port, message, timeout=timeout)
                
                if success:
                    sent_count += 1
                    log.info("Sent %s to %s (%s:%d)", status.upper(), peer.display_name, peer.ip, peer.tcp_port)
                else:
                    log.warning("Failed to send %s to %s (%s:%d) - peer may be offline or unreachable", 
                              status.upper(), peer.display_name, peer.ip, peer.tcp_port)
                    failed_peers.append(f"{peer.display_name} ({peer.ip})")
            except Exception as e:
                log.warning("Error sending %s to %s: %s", status, peer.display_name, e)
                failed_peers.append(f"{peer.display_name} ({peer.ip})")
        
        log.info("=" * 60)
        log.info("Broadcast complete: %d/%d sent successfully", sent_count, len(friends))
        if failed_peers:
            log.warning("Failed to reach: %s", ", ".join(failed_peers))
        log.info("=" * 60)
    
    def send_status_to_peer(self, peer_id: str, status: str):
        if status not in ("online", "offline"):
            log.warning("[STATUS] Invalid status: %s", status)
            return False
        
        with self.router._lock:
            peer = self.router._peers.get(peer_id)
        
        if not peer:
            log.warning("[STATUS] Peer %s not found", peer_id)
            return False
        
        if not peer.ip or not peer.tcp_port or peer.tcp_port == 0:
            log.warning("[STATUS] Peer %s has invalid IP=%s or port=%s", peer_id, peer.ip, peer.tcp_port)
            return False
        
        try:
            if status == "online":
                avatar_base64 = None
                avatar_path = getattr(self.router, 'avatar_path', None)
                if avatar_path:
                    try:
                        avatar_file = Path(avatar_path)
                        if avatar_file.exists():
                            with open(avatar_file, 'rb') as f:
                                avatar_base64 = base64.b64encode(f.read()).decode('utf-8')
                    except Exception as e:
                        log.warning("Failed to read avatar file %s: %s", avatar_path, e)
                
                message = Message.create_online_status(
                    sender_id=self.router.peer_id,
                    sender_name=self.router.display_name or "Unknown",
                    receiver_id=peer.peer_id,
                    avatar_base64=avatar_base64
                )
            else:
                message = Message.create_offline_status(
                    sender_id=self.router.peer_id,
                    sender_name=self.router.display_name or "Unknown",
                    receiver_id=peer.peer_id
                )
            
            timeout = 1.0 if status == "offline" else None
            success = self.router.peer_client.send(peer.ip, peer.tcp_port, message, timeout=timeout)
            if success:
                log.info("[STATUS] ✓ Sent %s to %s", status.upper(), peer.display_name)
                return True
            else:
                log.debug("[STATUS] Failed to send %s to %s", status.upper(), peer.display_name)
                return False
        except Exception as e:
            log.debug("[STATUS] Error sending %s to %s: %s", status, peer_id, e)
            return False
