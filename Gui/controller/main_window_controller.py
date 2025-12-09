from collections import defaultdict
from typing import Dict, List, Optional
import logging
import os
import base64
import time

from PySide6.QtCore import QObject, Signal, QTimer, Slot
from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from Core.core_api import ChatCore

log = logging.getLogger(__name__)


class MainWindowController(QObject):
    
    chat_list_updated = Signal(list)
    message_received = Signal(dict)
    chat_selected = Signal(str, str)
    show_friend_request_dialog = Signal(str, str)
    show_message_box = Signal(str, str, str)
    load_chat_history = Signal(str, list)
    
    def __init__(self, username: str, display_name: str, tcp_port: int):
        super().__init__()
        
        self.username = username
        self.display_name = display_name
        self.tcp_port = tcp_port
        
        from app.user_manager import _normalize_username
        normalized_username = _normalize_username(self.username)
        
        self.chat_core = ChatCore(
            username=normalized_username,
            display_name=self.display_name,
            tcp_port=self.tcp_port,
            on_message_callback=None,
            on_peer_update=None,
        )
        
        self.chat_core.signals.message_received.connect(self._on_message_received_signal)
        self.chat_core.signals.peer_updated.connect(self._on_peer_updated_signal)
        self.chat_core.signals.friend_request_received.connect(self._on_friend_request_received_signal)
        self.chat_core.signals.friend_accepted.connect(self._on_friend_accepted_signal)
        self.chat_core.signals.friend_rejected.connect(self._on_friend_rejected_signal)
        
        self.peers: Dict[str, Dict] = {}
        self.unread_counts = defaultdict(int)
        self.current_peer_id: str = ""
        self._pending_files = {}
        self._preview_items = {}
        self.pending_friend_requests: Dict[str, str] = {}
        self._active_request_dialogs: Dict[str, QDialog] = {}
        
        self._peer_refresh_timer = None
    
    def start(self, parent_widget=None):
        try:
            self.chat_core.start()
        except Exception as exc:
            self.show_message_box.emit("error", "ChatCore Error", f"Failed to start chat core: {exc}")
            raise
        
        self._update_peers_from_core()
        
        # Clean up orphaned chat folders (folders without corresponding peers)
        self._cleanup_orphaned_chat_folders()
        
        self._refresh_chat_list()
        
        self._peer_refresh_timer = QTimer()
        self._peer_refresh_timer.setInterval(5000)
        self._peer_refresh_timer.timeout.connect(self._update_peers_from_core)
        self._peer_refresh_timer.start()
    
    def stop(self):
        if self._peer_refresh_timer:
            self._peer_refresh_timer.stop()
        self.chat_core.stop()
    
    def _update_peers_from_core(self):
        peers = self.chat_core.get_known_peers()
        self.peers = {peer["peer_id"]: peer for peer in peers}
        self._refresh_chat_list()
    
    def _get_conversations(self) -> List[Dict]:
        conversations = []
        
        for peer_id, peer in self.peers.items():
            history = self.chat_core.get_message_history(peer_id)
            last_message = history[-1] if history else None
            conversations.append({
                "peer_id": peer_id,
                "peer_name": peer.get("display_name", "Unknown"),
                "last_message": last_message["content"] if last_message else "",
                "last_message_time": last_message["timestamp"] if last_message else 0,
                "time_str": last_message["time_str"] if last_message else "",
                "unread_count": self.unread_counts.get(peer_id, 0),
                "is_online": peer.get("status", "") == "online",
            })
        
        conversations.sort(key=lambda c: c["last_message_time"], reverse=True)
        return conversations
    
    def _refresh_chat_list(self):
        conversations = self._get_conversations()
        self.chat_list_updated.emit(conversations)
        
        # Don't auto-select first peer - let user choose
    
    def on_chat_selected(self, chat_id: str, chat_name: str):
        if not chat_id:
            return
        self.current_peer_id = chat_id
        self.unread_counts[chat_id] = 0
        history = self.chat_core.get_message_history(chat_id)
        self.load_chat_history.emit(chat_id, history)
        # Emit chat_selected signal to update header
        self.chat_selected.emit(chat_id, chat_name)
        self._refresh_chat_list()
    
    # Suggestions feature removed - no longer needed

    @Slot(str, int)
    def add_friend_by_ip(self, ip: str, port: int):
        """Add a friend by IP address and port."""
        try:
            print(f"[Controller] add_friend_by_ip called with IP={ip}, Port={port}, Type: {type(port)}")
            log.info(f"[Controller] add_friend_by_ip called with IP={ip}, Port={port}, Type: {type(port)}")
            
            # Convert port to int if it's a string
            if isinstance(port, str):
                try:
                    port = int(port)
                except ValueError:
                    log.error(f"[Controller] Invalid port value: {port}")
                    self.show_message_box.emit("warning", "Add Friend", f"Invalid port: {port}")
                    return
            
            ip = ip.strip() if ip else ""
            
            if not ip or not port:
                log.warning(f"[Controller] Empty IP or port: IP={ip}, Port={port}")
                self.show_message_box.emit("warning", "Add Friend", "Please enter a valid IP and port.")
                return
            
            if port < 1 or port > 65535:
                log.warning(f"[Controller] Port out of range: {port}")
                self.show_message_box.emit("warning", "Add Friend", "Port must be between 1 and 65535.")
                return
            
            print(f"[Controller] [Add Friend] Attempting to add peer at {ip}:{port}")
            log.info(f"[Controller] [Add Friend] Attempting to add peer at {ip}:{port}")
            
            print(f"[Controller] Calling chat_core.add_peer_by_ip...")
            success, result = self.chat_core.add_peer_by_ip(ip, port, display_name="Unknown")
            print(f"[Controller] add_peer_by_ip returned: success={success}, result={result}")
            if success:
                log.info(f"[Controller] [Add Friend] Successfully added peer at {ip}:{port}")
                self.show_message_box.emit("info", "Add Friend", f"Added friend at {ip}:{port}")
                self._update_peers_from_core()
                self._refresh_chat_list()
            else:
                log.error(f"[Controller] [Add Friend] Failed to add peer at {ip}:{port}: {result}")
                self.show_message_box.emit("warning", "Add Friend", f"Failed to add friend: {result}")
        except Exception as e:
            print(f"[Controller] Exception in add_friend_by_ip: {e}")
            import traceback
            traceback.print_exc()
            log.error(f"[Controller] Exception in add_friend_by_ip: {e}", exc_info=True)
            self.show_message_box.emit("error", "Add Friend Error", f"An error occurred: {e}")
    
    def send_message(self, message_text: str) -> bool:
        if not self.current_peer_id:
            self.show_message_box.emit("info", "Select chat", "Please choose a conversation before sending messages.")
            return False
        
        preview_items = getattr(self, '_preview_items', {})
        message_text = message_text.strip() if message_text else ""
        
        if not message_text and not preview_items:
            return False
        
        success_count = 0
        total_items = len(preview_items) + (1 if message_text else 0)
        
        for file_name, (file_data_base64, is_image) in preview_items.items():
            msg_type = "image" if is_image else "file"
            content = "" if is_image else file_name
            
            try:
                success = self.chat_core.send_message(
                    self.current_peer_id,
                    content,
                    msg_type=msg_type,
                    file_name=file_name,
                    file_data=file_data_base64,
                    audio_data=None
                )
                
                if success:
                    success_count += 1
            except Exception as e:
                pass
        
        if message_text:
            try:
                print(f"[Controller] Sending text message to peer_id={self.current_peer_id[:8]}")
                success = self.chat_core.send_message(
                    self.current_peer_id,
                    message_text,
                    msg_type="text",
                    file_name=None,
                    file_data=None,
                    audio_data=None
                )
                print(f"[Controller] send_message returned: success={success}")
                if success:
                    success_count += 1
                    print(f"[Controller] success_count incremented to {success_count}")
                else:
                    print(f"[Controller] send_message failed!")
            except Exception as e:
                print(f"[Controller] Exception in send_message: {e}")
                import traceback
                traceback.print_exc()
        
        if preview_items:
            self._preview_items = {}
            if hasattr(self, 'clear_preview_callback'):
                self.clear_preview_callback()
        
        print(f"[Controller] Send complete: success_count={success_count}, total_items={total_items}")
        if success_count == 0 and total_items > 0:
            print(f"[Controller] Showing 'Failed to send' dialog")
            self.show_message_box.emit("warning", "Network error", "Failed to send message. Peer might be offline.")
        elif success_count > 0 and success_count < total_items:
            self.show_message_box.emit("warning", "Partial send", f"Sent {success_count}/{total_items} items. Some may have failed.")
        
        return success_count > 0
    
    def handle_file_attached(self, file_path: str, file_name: str, file_data_base64: str, is_image: bool):
        if not hasattr(self, '_preview_items'):
            self._preview_items = {}
        
        self._preview_items[file_name] = (file_data_base64, is_image)
        
        if hasattr(self, 'add_preview_callback'):
            self.add_preview_callback(file_name, file_data_base64, is_image)
    
    
    def _on_message_received_signal(self, payload: Dict):
        try:
            peer_id = payload.get("peer_id", "")
            sender_name = payload.get("sender_name", "Unknown")
            content = payload.get("content", "")
            is_sender = payload.get("is_sender", False)
            timestamp = payload.get("timestamp", 0)
            time_str = payload.get("time_str", "")
            
            if not is_sender and peer_id != self.current_peer_id:
                self.unread_counts[peer_id] = self.unread_counts.get(peer_id, 0) + 1
            
            file_name = payload.get("file_name")
            file_data = payload.get("file_data")
            
            msg_type = payload.get("msg_type", "text")
            
            if peer_id == self.current_peer_id:
                if msg_type == "image" or msg_type == "file":
                    display_content = ""
                else:
                    display_content = content
                
                payload["display_content"] = display_content
                
                if file_name and file_data and not payload.get("is_sender", False):
                    saved_path = self._save_received_file(peer_id, file_name, file_data)
                    if saved_path:
                        payload["local_file_path"] = saved_path
            
            self.message_received.emit(payload)
            self._refresh_chat_list()
        except Exception as e:
            import traceback
    
    def _get_peer_folder_name(self, peer_id: str) -> str:
        from app.user_manager import _normalize_username
        
        if peer_id in self.peers:
            peer_info = self.peers[peer_id]
            display_name = peer_info.get("display_name", peer_id)
            return _normalize_username(display_name)
        
        return _normalize_username(peer_id[:8])
    
    def _save_received_file(self, peer_id: str, file_name: str, file_data_base64: str):
        try:
            if hasattr(self.chat_core, 'router') and hasattr(self.chat_core.router, 'data_manager'):
                data_manager = self.chat_core.router.data_manager
                if data_manager:
                    file_data = base64.b64decode(file_data_base64)
                    file_path = data_manager.save_file_for_peer(peer_id, file_name, file_data)
                    return str(file_path)
            
        except Exception as e:
            import traceback
    
    def _on_peer_updated_signal(self, peer_info: Dict):
        try:
            peer_id = peer_info.get("peer_id", "")
            if peer_id:
                old_status = self.peers.get(peer_id, {}).get("status", "")
                self.peers[peer_id] = peer_info
                new_status = peer_info.get("status", "")
                
                # If status changed and this is the current peer, update header
                if peer_id == self.current_peer_id and old_status != new_status:
                    peer_name = peer_info.get("display_name", "Unknown")
                    self.chat_selected.emit(peer_id, peer_name)
                    # Also update header status directly
                    is_online = new_status == "online"
                    if hasattr(self, '_update_header_status_callback'):
                        self._update_header_status_callback(peer_id, is_online)
                
                # Update chat list to reflect status change
                # Also emit signal to update status in list immediately
                is_online = new_status == "online"
                if hasattr(self, '_update_peer_status_callback'):
                    self._update_peer_status_callback(peer_id, is_online)
                
                self._refresh_chat_list()
        except Exception as e:
            import traceback
    
    # Temp peer signals removed - discovery feature removed
    
    def _on_friend_request_received_signal(self, peer_id: str, display_name: str):
        try:
            log.info("Friend request signal received for %s (%s)", display_name, peer_id)
            
            if peer_id in self.peers:
                log.debug("Ignoring friend request from %s: already a friend", peer_id)
                return
            
            if peer_id in self.pending_friend_requests:
                log.debug("Ignoring duplicate friend request from %s", peer_id)
                return
            
            self.pending_friend_requests[peer_id] = display_name
            log.info("Showing friend request dialog for %s (%s)", display_name, peer_id)
            
            self.show_friend_request_dialog.emit(peer_id, display_name)
        except Exception as e:
            import traceback
            log.error(f"Error in _on_friend_request_received_signal: {e}")
            self.show_message_box.emit("error", "Error", f"Error processing friend request: {e}")
    
    def on_accept_friend_request(self, peer_id: str):
        display_name = self.pending_friend_requests.pop(peer_id, "Unknown")
        
        success = self.chat_core.accept_friend(peer_id)
        if success:
            self._update_peers_from_core()
            self._refresh_chat_list()
            
            self.current_peer_id = peer_id
            self.unread_counts[peer_id] = 0
            history = self.chat_core.get_message_history(peer_id)
            self.load_chat_history.emit(peer_id, history)
            self._refresh_chat_list()
            
            self.show_message_box.emit("info", "Friend Added", f"You are now friends with {display_name}! Chat window opened.")
        else:
            self.show_message_box.emit("warning", "Error", f"Failed to accept friend request from {display_name}.")
    
    def on_reject_friend_request(self, peer_id: str):
        display_name = self.pending_friend_requests.pop(peer_id, "Unknown")
        self.chat_core.reject_friend(peer_id)
    
    def _on_friend_accepted_signal(self, peer_id: str):
        try:
            self.pending_friend_requests.pop(peer_id, None)
            
            self._update_peers_from_core()
            self._refresh_chat_list()
            
            peer_name = "Unknown"
            for peer in self.chat_core.get_known_peers():
                if peer["peer_id"] == peer_id:
                    peer_name = peer.get("display_name", "Unknown")
                    break
            
            self.current_peer_id = peer_id
            self.unread_counts[peer_id] = 0
            history = self.chat_core.get_message_history(peer_id)
            self.load_chat_history.emit(peer_id, history)
            self._refresh_chat_list()
            
            self.show_message_box.emit("info", "Friend Request Accepted", f"{peer_name} accepted your friend request! Chat window opened.")
        except Exception as e:
            import traceback
            log.error(f"Error in _on_friend_accepted_signal: {e}")
            self.show_message_box.emit("error", "Error", f"Error processing friend accept: {e}")
    
    def _on_friend_rejected_signal(self, peer_id: str):
        try:
            peer_name = "Unknown"
            known_peers = self.chat_core.get_known_peers()
            for peer in known_peers:
                if peer["peer_id"] == peer_id:
                    peer_name = peer.get("display_name", "Unknown")
                    break
            
            self.show_message_box.emit("warning", "Friend Request Rejected", f"{peer_name} rejected your friend request.")
        except Exception as e:
            import traceback
    
    def _cleanup_offline_peers(self):
        if self.chat_core:
            removed_count = self.chat_core.cleanup_offline_peers()
            if removed_count > 0:
                log.info("Cleaned up %s offline peers", removed_count)
                self._refresh_chat_list()
    
    def remove_friend(self, peer_id: str):
        """Remove a friend from peer list"""
        try:
            log.info(f"[Controller] Removing friend {peer_id}")
            
            # Get peer name
            peer_info = self.peers.get(peer_id, {})
            peer_name = peer_info.get('display_name', 'Unknown')
            
            # Send OFFLINE to peer before removing (so they know we're gone)
            if self.chat_core.router and self.chat_core.router.status_broadcaster:
                log.info(f"[Controller] Sending OFFLINE to {peer_name} before removing")
                self.chat_core.router.status_broadcaster.send_status_to_peer(peer_id, "offline")
            
            # Remove from router runtime first (to prevent reload from storage)
            if self.chat_core.router:
                with self.chat_core.router._lock:
                    if peer_id in self.chat_core.router._peers:
                        del self.chat_core.router._peers[peer_id]
                        log.info(f"[Controller] Removed peer {peer_id} from router runtime")
            
            # Remove from core storage
            if self.chat_core.router and self.chat_core.router.data_manager:
                self.chat_core.router.data_manager.delete_peer(peer_id)
                log.info(f"[Controller] Deleted peer {peer_id} from storage")
            
            # Remove from controller runtime
            if peer_id in self.peers:
                del self.peers[peer_id]
            
            if peer_id in self.unread_counts:
                del self.unread_counts[peer_id]
            
            # Also delete chat history folder completely
            if self.chat_core.router and self.chat_core.router.data_manager:
                from pathlib import Path
                import shutil
                chat_folder = Path(self.chat_core.router.data_manager.root) / "chats" / peer_id
                if chat_folder.exists() and chat_folder.is_dir():
                    try:
                        shutil.rmtree(str(chat_folder))
                        log.info(f"[Controller] Deleted chat folder for removed friend: {chat_folder}")
                    except Exception as e:
                        log.error(f"[Controller] Failed to delete chat folder {chat_folder}: {e}", exc_info=True)
                else:
                    log.warning(f"[Controller] Chat folder does not exist: {chat_folder}")
            
            # Clear current selection if this was the selected peer
            if self.current_peer_id == peer_id:
                self.current_peer_id = None
                self.load_chat_history.emit("", [])
            
            # Sync peers from router to ensure consistency
            self._update_peers_from_core()
            
            self.show_message_box.emit("info", "Friend Removed", f"{peer_name} has been removed from your friends list.")
            
        except Exception as e:
            log.error(f"[Controller] Error removing friend: {e}", exc_info=True)
            self.show_message_box.emit("error", "Error", f"Failed to remove friend: {e}")
    
    def _cleanup_orphaned_chat_folders(self):
        """Remove chat folders that don't have corresponding peers in peers.json"""
        try:
            if not self.chat_core.router or not self.chat_core.router.data_manager:
                return
            
            from pathlib import Path
            import shutil
            
            chats_dir = Path(self.chat_core.router.data_manager.root) / "chats"
            if not chats_dir.exists():
                return
            
            # Get list of peer IDs from peers.json
            known_peer_ids = set(self.peers.keys())
            
            # Check each folder in chats directory
            removed_count = 0
            for folder_path in chats_dir.iterdir():
                if folder_path.is_dir():
                    folder_name = folder_path.name
                    # If folder name (peer_id) is not in known peers, delete it
                    if folder_name not in known_peer_ids:
                        try:
                            shutil.rmtree(str(folder_path))
                            log.info(f"[Controller] Cleaned up orphaned chat folder: {folder_name}")
                            removed_count += 1
                        except Exception as e:
                            log.warning(f"[Controller] Failed to remove orphaned folder {folder_name}: {e}")
            
            if removed_count > 0:
                log.info(f"[Controller] Cleaned up {removed_count} orphaned chat folder(s)")
        
        except Exception as e:
            log.error(f"[Controller] Error cleaning up orphaned folders: {e}", exc_info=True)

