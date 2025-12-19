import base64
import json
import logging
from pathlib import Path
from typing import Optional

from Core.models.message import Message
from Core.models.peer_info import PeerInfo

log = logging.getLogger(__name__)

class MessageHandlers:

    def __init__(self, router):
        self.router = router
    
    def handle_hello(self, message: Message, sender_ip: str = "", sender_port: int = 0):
        log.info("[HELLO] Received from %s (%s) at %s:%s", message.sender_name, message.sender_id, sender_ip, sender_port)
        
        if message.sender_id == self.router.peer_id:
            log.warning("[HELLO] Ignoring HELLO from myself (loopback)")
            return
        
        sender_tcp_port = 0
        sender_real_ip = sender_ip
        try:
            content_data = json.loads(message.content) if message.content else {}
            sender_tcp_port = content_data.get("tcp_port", 0)
            sender_real_ip = content_data.get("sender_ip", sender_ip)
            log.info("[HELLO] Extracted sender_ip=%s, tcp_port=%s from message", sender_real_ip, sender_tcp_port)
        except:
            log.warning("[HELLO] Could not extract from HELLO message, using socket: %s:%s", sender_ip, sender_port)
            sender_tcp_port = sender_port
        
        try:
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect((sender_ip, 80))
                local_ip = s.getsockname()[0]
                s.close()
            except:
                local_ip = ""
            
            reply_msg = Message.create_hello_reply(
                sender_id=self.router.peer_id,
                sender_name=self.router.display_name or "Unknown",
                receiver_id=message.sender_id,
                peer_ip=local_ip,
                peer_tcp_port=self.router.tcp_port
            )
            
            log.info("[HELLO] Replying with our info: peer_id=%s, name=%s, ip=%s, port=%s", 
                    self.router.peer_id, self.router.display_name, local_ip, self.router.tcp_port)
            
            success = self.router.peer_client.send(sender_real_ip, sender_tcp_port, reply_msg)
            if success:
                log.info("[HELLO] Successfully sent HELLO_REPLY to %s:%s", sender_real_ip, sender_tcp_port)
            else:
                log.warning("[HELLO] Failed to send HELLO_REPLY to %s:%s", sender_real_ip, sender_tcp_port)
        except Exception as e:
            log.error("[HELLO] Error sending HELLO_REPLY: %s", e, exc_info=True)
    
    def handle_hello_reply(self, message: Message, sender_ip: str = ""):
        log.info("[HELLO_REPLY] Received from %s (%s) at %s", message.sender_name, message.sender_id, sender_ip)
        
        if message.sender_id == self.router.peer_id:
            log.warning("[HELLO_REPLY] Ignoring HELLO_REPLY from myself (loopback)")
            return
        
        try:
            reply_data = json.loads(message.content)
            actual_peer_id = reply_data.get("peer_id", message.sender_id)
            display_name = reply_data.get("display_name", message.sender_name)
            peer_ip = reply_data.get("ip", sender_ip if sender_ip else "")
            peer_tcp_port = int(reply_data.get("tcp_port", 0))
            
            log.info("[HELLO_REPLY] Parsed: peer_id=%s, name=%s, ip=%s, port=%s", 
                    actual_peer_id, display_name, peer_ip, peer_tcp_port)
            
            if peer_tcp_port < 1 or peer_tcp_port > 65535:
                log.warning("[HELLO_REPLY] Invalid tcp_port %s", peer_tcp_port)
                return
            
            old_peer_id = None
            with self.router._lock:
                temp_peer_entry = None
                for pid, peer in list(self.router._peers.items()):
                    if peer.ip == peer_ip and peer.tcp_port == peer_tcp_port:
                        temp_peer_entry = (pid, peer)
                        log.info("[HELLO_REPLY] Found matching peer by IP:Port - peer_id=%s", pid)
                        break
                
                if temp_peer_entry:
                    old_peer_id, old_peer = temp_peer_entry
                    if old_peer_id != actual_peer_id:
                        del self.router._peers[old_peer_id]
                        log.info("[HELLO_REPLY] Replacing temp peer_id %s with actual %s", old_peer_id, actual_peer_id)
                        if self.router.data_manager:
                            self.router.data_manager.delete_peer(old_peer_id)
                            log.info("[HELLO_REPLY] Deleted temp peer %s from storage", old_peer_id)
                
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
                
                peer_info.display_name = display_name
                peer_info.ip = peer_ip
                peer_info.tcp_port = peer_tcp_port
                
                if self.router.data_manager:
                    self.router.data_manager.update_peer(peer_info)
                    log.info("[HELLO_REPLY] Saved peer %s (%s)", display_name, actual_peer_id)
                
                if self.router._on_peer_callback:
                    try:
                        self.router._on_peer_callback(peer_info)
                        log.info("[HELLO_REPLY] Notified peer callback for %s", actual_peer_id)
                    except Exception as e:
                        log.error("[HELLO_REPLY] Error in peer callback: %s", e, exc_info=True)
            
            # HELLO_REPLY = Accept friend request automatically
            log.info("[HELLO_REPLY] Auto-accepting friend request from %s (%s)", display_name, actual_peer_id)
            
            # Clean up request tracking
            with self.router._lock:
                self.router._outgoing_requests.discard(actual_peer_id)
                self.router._incoming_requests.discard(actual_peer_id)
            
            # Verify peer exists and has valid IP/port before sending status
            with self.router._lock:
                peer_info = self.router._peers.get(actual_peer_id)
            
            if not peer_info:
                log.warning("[HELLO_REPLY] Cannot send ONLINE: peer %s not found in peers list", actual_peer_id)
                return
            
            if not peer_info.ip or not peer_info.tcp_port or peer_info.tcp_port == 0:
                log.warning("[HELLO_REPLY] Cannot send ONLINE: peer %s has invalid IP=%s or port=%s", 
                           actual_peer_id, peer_info.ip, peer_info.tcp_port)
                return
            
            # Send ONLINE status to complete the handshake
            log.info("[HELLO_REPLY] Sending ONLINE status to %s (%s:%s)", display_name, peer_info.ip, peer_info.tcp_port)
            from .status_broadcaster import StatusBroadcaster
            status_mgr = StatusBroadcaster(self.router)
            success = status_mgr.send_status_to_peer(actual_peer_id, "online")
            if not success:
                log.debug("[HELLO_REPLY] Failed to send ONLINE status to %s (may retry later)", display_name)
                        
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            log.error("[HELLO_REPLY] Failed to parse: %s", e, exc_info=True)
    
    def handle_status_message(self, message: Message, sender_ip: str = ""):
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
            
            if msg_type == "ONLINE" and message.content:
                try:
                    content_data = json.loads(message.content)
                    if "avatar_base64" in content_data and content_data["avatar_base64"]:
                        try:
                            avatar_data = base64.b64decode(content_data["avatar_base64"])
                            
                            if self.router.data_manager:
                                peer_dir = self.router.data_manager.root / "chats" / peer.peer_id
                                peer_dir.mkdir(parents=True, exist_ok=True)
                                avatar_file = peer_dir / "avatar.jpg"
                                with open(avatar_file, 'wb') as f:
                                    f.write(avatar_data)
                                
                                peer.avatar_path = str(avatar_file)
                                log.info("[STATUS] Saved avatar for %s to %s", peer.display_name, avatar_file)
                                self.router.data_manager.update_peer(peer)
                        except Exception as e:
                            log.warning("[STATUS] Failed to save avatar for %s: %s", peer.display_name, e)
                except (json.JSONDecodeError, ValueError):
                    pass
            
            log.info("[STATUS] ✓ Updated %s (%s): %s -> %s (IP: %s, Port: %s)", 
                    peer.display_name, message.sender_id, old_status, new_status,
                    peer.ip, peer.tcp_port)
            
            if msg_type == "ONLINE" and old_status != "online":
                log.info("[STATUS] Replying ONLINE back to %s", peer.display_name)
                try:
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
                    
                    reply_msg = Message.create_online_status(
                        sender_id=self.router.peer_id,
                        sender_name=self.router.display_name or "Unknown",
                        receiver_id=peer.peer_id,
                        avatar_base64=avatar_base64
                    )
                    self.router.peer_client.send(peer.ip, peer.tcp_port, reply_msg)
                    log.info("[STATUS] ✓ Sent ONLINE reply to %s", peer.display_name)
                except Exception as e:
                    log.debug("[STATUS] Failed to send ONLINE reply to %s: %s", peer.display_name, e)
            
            if self.router._on_peer_callback:
                try:
                    self.router._on_peer_callback(peer)
                    log.info("[STATUS] ✓ Triggered peer callback for %s", peer.display_name)
                except Exception as e:
                    log.error("[STATUS] ✗ Error in peer callback for %s: %s", message.sender_id, e, exc_info=True)
    
    def handle_call_request(self, message: Message, sender_ip: str = ""):
        log.info("[Call] Received CALL_REQUEST from %s (%s)", message.sender_name, message.sender_id)
        
        try:
            content_data = json.loads(message.content) if message.content else {}
            call_type = content_data.get("call_type", "voice")
            audio_port = content_data.get("audio_port", 0)
            video_port = content_data.get("video_port", 0)
            
            log.info("[Call] Type: %s, Audio port: %s, Video port: %s", call_type, audio_port, video_port)
            
            if self.router._on_call_request_callback:
                try:
                    self.router._on_call_request_callback(
                        message.sender_id,
                        message.sender_name,
                        call_type,
                        audio_port,
                        video_port,
                        sender_ip
                    )
                except Exception as e:
                    log.error("[Call] Error in call request callback: %s", e, exc_info=True)
        except Exception as e:
            log.error("[Call] Error handling CALL_REQUEST: %s", e, exc_info=True)
    
    def handle_call_accept(self, message: Message, sender_ip: str = ""):
        log.info("[Call] Received CALL_ACCEPT from %s (%s)", message.sender_name, message.sender_id)
        
        try:
            content_data = json.loads(message.content) if message.content else {}
            audio_port = content_data.get("audio_port", 0)
            video_port = content_data.get("video_port", 0)
            
            log.info("[Call] Peer audio port: %s, video port: %s", audio_port, video_port)
            
            if self.router._on_call_accept_callback:
                try:
                    self.router._on_call_accept_callback(
                        message.sender_id,
                        audio_port,
                        video_port
                    )
                except Exception as e:
                    log.error("[Call] Error in call accept callback: %s", e, exc_info=True)
        except Exception as e:
            log.error("[Call] Error handling CALL_ACCEPT: %s", e, exc_info=True)
    
    def handle_call_reject(self, message: Message, sender_ip: str = ""):
        log.info("[Call] Received CALL_REJECT from %s (%s)", message.sender_name, message.sender_id)
        
        if self.router._on_call_reject_callback:
            try:
                self.router._on_call_reject_callback(message.sender_id)
            except Exception as e:
                log.error("[Call] Error in call reject callback: %s", e, exc_info=True)
    
    def handle_call_end(self, message: Message, sender_ip: str = ""):
        log.info("[Call] Received CALL_END from %s (%s)", message.sender_name, message.sender_id)
        
        if self.router._on_call_end_callback:
            try:
                self.router._on_call_end_callback(message.sender_id)
            except Exception as e:
                log.error("[Call] Error in call end callback: %s", e, exc_info=True)
