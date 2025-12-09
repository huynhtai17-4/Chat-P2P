import logging
import json
from typing import Optional

from Core.models.message import Message
from Core.models.peer_info import PeerInfo

log = logging.getLogger(__name__)

class MessageHandlers:

    def __init__(self, router):
        self.router = router
    
    def handle_hello(self, message: Message, sender_ip: str = "", sender_port: int = 0):
        """Handle HELLO handshake - reply with HELLO_REPLY containing our peer info"""
        log.info("[HELLO] Received from %s (%s) at %s:%s (socket)", message.sender_name, message.sender_id, sender_ip, sender_port)
        log.info("[HELLO] My peer_id=%s, sender_id=%s", self.router.peer_id, message.sender_id)
        
        # Ignore HELLO from ourselves (loopback)
        if message.sender_id == self.router.peer_id:
            log.warning("[HELLO] Ignoring HELLO from myself (loopback)")
            return
        
        # Extract sender's real TCP port from message content
        sender_tcp_port = 0
        try:
            content_data = json.loads(message.content) if message.content else {}
            sender_tcp_port = content_data.get("tcp_port", 0)
            log.info("[HELLO] Extracted sender's tcp_port=%s from message", sender_tcp_port)
        except:
            log.warning("[HELLO] Could not extract tcp_port from HELLO message, using socket port %s", sender_port)
            sender_tcp_port = sender_port
        
        # Reply with our peer info
        try:
            # Use our local IP for the reply
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect((sender_ip, 80))  # Use port 80 just to get route
                local_ip = s.getsockname()[0]
                s.close()
            except:
                local_ip = "127.0.0.1"
            
            reply_msg = Message.create_hello_reply(
                sender_id=self.router.peer_id,
                sender_name=self.router.display_name or "Unknown",
                receiver_id=message.sender_id,
                peer_ip=local_ip,
                peer_tcp_port=self.router.tcp_port
            )
            
            log.info("[HELLO] Replying with our info: peer_id=%s, name=%s, ip=%s, port=%s", 
                    self.router.peer_id, self.router.display_name, local_ip, self.router.tcp_port)
            
            # Send reply back to sender's TCP port (not socket port!)
            log.info("[HELLO] Sending HELLO_REPLY to %s:%s (sender's tcp_port)", sender_ip, sender_tcp_port)
            success = self.router.peer_client.send(sender_ip, sender_tcp_port, reply_msg)
            if success:
                log.info("[HELLO] Successfully sent HELLO_REPLY to %s:%s", sender_ip, sender_tcp_port)
            else:
                log.warning("[HELLO] Failed to send HELLO_REPLY to %s:%s", sender_ip, sender_tcp_port)
        except Exception as e:
            log.error("[HELLO] Error sending HELLO_REPLY: %s", e, exc_info=True)
    
    def handle_hello_reply(self, message: Message, sender_ip: str = ""):
        """Handle HELLO_REPLY - update peer info with actual peer_id and details"""
        log.info("[HELLO_REPLY] Received from %s (%s) at %s", message.sender_name, message.sender_id, sender_ip)
        log.info("[HELLO_REPLY] My peer_id=%s, sender_id=%s", self.router.peer_id, message.sender_id)
        
        # Ignore HELLO_REPLY from ourselves (loopback)
        if message.sender_id == self.router.peer_id:
            log.warning("[HELLO_REPLY] Ignoring HELLO_REPLY from myself (loopback)")
            return
        
        try:
            reply_data = json.loads(message.content)
            actual_peer_id = reply_data.get("peer_id", message.sender_id)
            display_name = reply_data.get("display_name", message.sender_name)
            peer_ip = reply_data.get("ip", sender_ip if sender_ip else "127.0.0.1")
            peer_tcp_port = int(reply_data.get("tcp_port", 0))
            
            log.info("[HELLO_REPLY] Parsed: peer_id=%s, name=%s, ip=%s, port=%s", 
                    actual_peer_id, display_name, peer_ip, peer_tcp_port)
            
            if peer_tcp_port < 1 or peer_tcp_port > 65535:
                log.warning("[HELLO_REPLY] Invalid tcp_port %s", peer_tcp_port)
                return
            
            old_peer_id = None
            with self.router._lock:
                # Find temp peer (the one we created when adding by IP)
                # Match by IP and Port from the HELLO_REPLY data
                temp_peer_entry = None
                for pid, peer in list(self.router._peers.items()):
                    # Check if this is our temp peer by matching IP:Port we added
                    if peer.ip == peer_ip and peer.tcp_port == peer_tcp_port:
                        temp_peer_entry = (pid, peer)
                        log.info("[HELLO_REPLY] Found matching peer by IP:Port - peer_id=%s", pid)
                        break
                
                if temp_peer_entry:
                    old_peer_id, old_peer = temp_peer_entry
                    # If temp peer_id is different from actual, replace it
                    if old_peer_id != actual_peer_id:
                        del self.router._peers[old_peer_id]
                        log.info("[HELLO_REPLY] Replacing temp peer_id %s with actual %s", old_peer_id, actual_peer_id)
                        # Also remove from emitted set if exists
                        self.router._friend_request_emitted.discard(old_peer_id)
                        # DELETE old peer from storage
                        if self.router.data_manager:
                            self.router.data_manager.delete_peer(old_peer_id)
                            log.info("[HELLO_REPLY] Deleted temp peer %s from storage", old_peer_id)
                
                # Create or update peer with actual info
                if actual_peer_id in self.router._peers:
                    peer_info = self.router._peers[actual_peer_id]
                    log.info("[HELLO_REPLY] Updating existing peer %s", actual_peer_id)
                else:
                    peer_info = PeerInfo(
                        peer_id=actual_peer_id,
                        display_name=display_name,
                        ip=peer_ip,
                        tcp_port=peer_tcp_port,
                        status="offline"
                    )
                    self.router._peers[actual_peer_id] = peer_info
                    log.info("[HELLO_REPLY] Created new peer %s", actual_peer_id)
                
                # Always update fields
                peer_info.display_name = display_name
                peer_info.ip = peer_ip
                peer_info.tcp_port = peer_tcp_port
                
                # Save to storage
                if self.router.data_manager:
                    self.router.data_manager.update_peer(peer_info)
                    log.info("[HELLO_REPLY] Saved peer %s (%s)", display_name, actual_peer_id)
                
                # Notify callback to update UI
                if self.router._on_peer_callback:
                    try:
                        self.router._on_peer_callback(peer_info)
                        log.info("[HELLO_REPLY] Notified peer callback for %s", actual_peer_id)
                    except Exception as e:
                        log.error("[HELLO_REPLY] Error in peer callback: %s", e, exc_info=True)
            
            # Send FRIEND_REQUEST to notify the peer
            log.info("[HELLO_REPLY] Sending FRIEND_REQUEST to %s (%s)", display_name, actual_peer_id)
            from .friend_request_manager import FriendRequestManager
            friend_mgr = FriendRequestManager(self.router)
            success = friend_mgr.send_friend_request(actual_peer_id)
            if success:
                log.info("[HELLO_REPLY] Successfully sent FRIEND_REQUEST to %s", actual_peer_id)
                
                # Send ONLINE status to the newly added peer
                log.info("[HELLO_REPLY] Sending ONLINE status to %s", actual_peer_id)
                from .status_broadcaster import StatusBroadcaster
                status_mgr = StatusBroadcaster(self.router)
                status_mgr.send_status_to_peer(actual_peer_id, "online")
            else:
                log.error("[HELLO_REPLY] Failed to send FRIEND_REQUEST to %s", actual_peer_id)
                        
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            log.error("[HELLO_REPLY] Failed to parse: %s", e, exc_info=True)
    
    def handle_friend_request(self, message: Message, sender_ip: str = ""):
        """Handle friend request - if peer not in list, auto-add them"""
        log.info("[FRIEND_REQUEST] From %s (%s) at %s", message.sender_name, message.sender_id, sender_ip)
        
        # Extract tcp_port from message content
        peer_tcp_port = 0
        try:
            content_data = json.loads(message.content) if message.content else {}
            peer_tcp_port = content_data.get("tcp_port", 0)
            log.info("[FRIEND_REQUEST] Extracted tcp_port=%s from content", peer_tcp_port)
        except:
            log.warning("[FRIEND_REQUEST] Could not parse tcp_port from content")
        
        with self.router._lock:
            if message.sender_id in self.router._peers:
                # Already a friend - update info if needed
                peer = self.router._peers[message.sender_id]
                if sender_ip and sender_ip != "0.0.0.0":
                    peer.ip = sender_ip
                if peer_tcp_port > 0:
                    peer.tcp_port = peer_tcp_port
                log.info("[FRIEND_REQUEST] Updated existing peer %s: ip=%s, port=%s", 
                        message.sender_id, peer.ip, peer.tcp_port)
            else:
                # Auto-add the peer who sent friend request
                log.info("[FRIEND_REQUEST] Auto-adding new peer %s (%s)", message.sender_name, message.sender_id)
                
                peer = PeerInfo(
                    peer_id=message.sender_id,
                    display_name=message.sender_name,
                    ip=sender_ip if sender_ip and sender_ip != "0.0.0.0" else "127.0.0.1",
                    tcp_port=peer_tcp_port,
                    status="offline"
                )
                self.router._peers[message.sender_id] = peer
                
                if self.router.data_manager:
                    self.router.data_manager.update_peer(peer)
                    log.info("[FRIEND_REQUEST] Saved new peer %s to storage", message.sender_name)
                
                # Notify peer callback to update UI
                if self.router._on_peer_callback:
                    try:
                        self.router._on_peer_callback(peer)
                        log.info("[FRIEND_REQUEST] Notified peer callback for new peer %s", message.sender_id)
                    except Exception as e:
                        log.error("[FRIEND_REQUEST] Error in peer callback: %s", e)
                
                # Send ONLINE status to the newly added peer
                log.info("[FRIEND_REQUEST] Sending ONLINE status to %s", message.sender_id)
                from .status_broadcaster import StatusBroadcaster
                status_mgr = StatusBroadcaster(self.router)
                status_mgr.send_status_to_peer(message.sender_id, "online")
            
            # Track incoming request
            if message.sender_id in self.router._incoming_requests:
                log.info("[FRIEND_REQUEST] Already in incoming_requests: %s", message.sender_id)
            else:
                self.router._incoming_requests.add(message.sender_id)
                log.info("[FRIEND_REQUEST] Added to incoming_requests: %s", message.sender_id)
        
        # Always emit friend request callback (don't track emitted to allow re-requesting)
        log.info("[FRIEND_REQUEST] Calling friend_request_callback for %s", message.sender_id)
        if self.router._on_friend_request_callback:
            try:
                self.router._on_friend_request_callback(message.sender_id, message.sender_name)
                log.info("[FRIEND_REQUEST] Successfully called callback for %s", message.sender_id)
            except Exception as e:
                log.error("[FRIEND_REQUEST] Error in callback for %s: %s", message.sender_id, e, exc_info=True)
        else:
            log.warning("[FRIEND_REQUEST] No callback registered!")
    
    def handle_friend_accept(self, message: Message, sender_ip: str = ""):
        """Handle friend accept - peer must already be in friends list"""
        log.info("Friend accepted by %s (%s)", message.sender_name, message.sender_id)
        
        with self.router._lock:
            if message.sender_id not in self.router._peers:
                log.warning("FRIEND_ACCEPT from %s (%s) but peer not in friends list", 
                           message.sender_name, message.sender_id)
                return
            
            peer_info = self.router._peers[message.sender_id]
            if sender_ip:
                peer_info.ip = sender_ip
            
            self.router._outgoing_requests.discard(message.sender_id)
            self.router._incoming_requests.discard(message.sender_id)
            self.router._friend_request_emitted.discard(message.sender_id)
        
        # Update storage
        if self.router.data_manager:
            self.router.data_manager.update_peer(peer_info)
            log.info("Updated peer %s (%s) after friend accept", peer_info.display_name, message.sender_id)
        
        # Notify callbacks
        if self.router._on_peer_callback:
            try:
                self.router._on_peer_callback(peer_info)
            except Exception as e:
                log.error("Error in _on_peer_callback for friend accept %s: %s", message.sender_id, e, exc_info=True)
        
        if self.router._on_friend_accepted_callback:
            try:
                self.router._on_friend_accepted_callback(message.sender_id)
            except Exception as e:
                log.error("Error in _on_friend_accepted_callback for %s: %s", message.sender_id, e, exc_info=True)
    
    def handle_friend_sync(self, message: Message, sender_ip: str = ""):
        """Handle FRIEND_SYNC - update peer IP/port info"""
        log.info("FRIEND_SYNC received from %s (%s)", message.sender_name, message.sender_id)
        
        try:
            sync_data = json.loads(message.content)
            peer_ip = sync_data.get("ip", sender_ip if sender_ip else "127.0.0.1")
            peer_tcp_port = int(sync_data.get("tcp_port", 0))
            
            if peer_tcp_port < 55000 or peer_tcp_port > 55199:
                log.warning("FRIEND_SYNC from %s has invalid tcp_port %s", message.sender_id, peer_tcp_port)
                return
            
            with self.router._lock:
                if message.sender_id in self.router._peers:
                    peer_info = self.router._peers[message.sender_id]
                    peer_info.ip = peer_ip
                    peer_info.tcp_port = peer_tcp_port
                    peer_info.display_name = message.sender_name
                else:
                    log.warning("FRIEND_SYNC from %s but peer not in friends list", message.sender_id)
                    return
            
            if self.router.data_manager:
                self.router.data_manager.update_peer(peer_info)
                log.info("Updated peer %s (%s) from FRIEND_SYNC", peer_info.display_name, message.sender_id)
            
            if self.router._on_peer_callback:
                try:
                    self.router._on_peer_callback(peer_info)
                except Exception as e:
                    log.error("Error in _on_peer_callback for FRIEND_SYNC %s: %s", message.sender_id, e, exc_info=True)
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            log.error("Failed to parse FRIEND_SYNC from %s: %s", message.sender_id, e)
    
    def handle_status_message(self, message: Message, sender_ip: str = ""):
        """Handle ONLINE/OFFLINE status messages"""
        msg_type = message.msg_type
        log.info("[STATUS] Received %s from %s (%s) at IP %s", 
                msg_type, message.sender_name, message.sender_id, sender_ip)
        
        with self.router._lock:
            if message.sender_id not in self.router._peers:
                log.warning("[STATUS] Ignoring %s from %s: not in friends list (have %s friends)", 
                          msg_type, message.sender_id, len(self.router._peers))
                return
            
            peer = self.router._peers[message.sender_id]
            new_status = "online" if msg_type == "ONLINE" else "offline"
            old_status = peer.status
            
            peer.status = new_status
            
            if sender_ip and sender_ip != "0.0.0.0" and sender_ip != "":
                peer.ip = sender_ip
            
            log.info("[STATUS] ✓ Updated %s (%s): %s -> %s (IP: %s, Port: %s)", 
                    peer.display_name, message.sender_id, old_status, new_status,
                    peer.ip, peer.tcp_port)
            
            # If we received ONLINE and our status changed from offline to online,
            # reply back with our ONLINE status to ensure mutual awareness
            if msg_type == "ONLINE" and old_status != "online":
                log.info("[STATUS] Replying ONLINE back to %s", peer.display_name)
                try:
                    reply_msg = Message.create_online_status(
                        sender_id=self.router.peer_id,
                        sender_name=self.router.display_name or "Unknown",
                        receiver_id=peer.peer_id
                    )
                    self.router.peer_client.send(peer.ip, peer.tcp_port, reply_msg)
                    log.info("[STATUS] ✓ Sent ONLINE reply to %s", peer.display_name)
                except Exception as e:
                    log.debug("[STATUS] Failed to send ONLINE reply to %s: %s", peer.display_name, e)
            
            # Trigger UI update
            if self.router._on_peer_callback:
                try:
                    self.router._on_peer_callback(peer)
                    log.info("[STATUS] ✓ Triggered peer callback for %s", peer.display_name)
                except Exception as e:
                    log.error("[STATUS] ✗ Error in peer callback for %s: %s", message.sender_id, e, exc_info=True)
    
    def handle_friend_reject(self, message: Message):
        """Handle friend reject"""
        log.info("Friend rejected by %s (%s)", message.sender_name, message.sender_id)
        with self.router._lock:
            self.router._outgoing_requests.discard(message.sender_id)
        if self.router._on_friend_rejected_callback:
            try:
                self.router._on_friend_rejected_callback(message.sender_id)
            except Exception as e:
                log.error("Error in _on_friend_rejected_callback for %s: %s", message.sender_id, e, exc_info=True)
