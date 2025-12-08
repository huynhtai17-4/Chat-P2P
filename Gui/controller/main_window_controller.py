from collections import defaultdict
from typing import Dict, List, Optional
import logging
import os
import base64
import time

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from Core.core_api import ChatCore

log = logging.getLogger(__name__)


class MainWindowController(QObject):
    
    chat_list_updated = Signal(list)
    suggestions_updated = Signal(list)
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
        self.chat_core.signals.temp_peer_updated.connect(self._on_temp_peer_updated_signal)
        self.chat_core.signals.temp_peer_removed.connect(self._on_temp_peer_removed_signal)
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
        
        self._suggestions_debounce_timer = None
        self._suggestions_pending_refresh = False
        self._peer_refresh_timer = None
        self._cleanup_timer = None
    
    def start(self, parent_widget=None):
        try:
            self.chat_core.start()
        except Exception as exc:
            self.show_message_box.emit("error", "ChatCore Error", f"Failed to start chat core: {exc}")
            raise
        
        self._suggestions_debounce_timer = QTimer()
        self._suggestions_debounce_timer.setSingleShot(True)
        self._suggestions_debounce_timer.setInterval(2000)
        self._suggestions_debounce_timer.timeout.connect(lambda: self._refresh_suggestions(debounced=True))
        self._suggestions_pending_refresh = False
        
        self._update_peers_from_core()
        self._refresh_chat_list()
        self._refresh_suggestions()
        
        self._peer_refresh_timer = QTimer()
        self._peer_refresh_timer.setInterval(5000)
        self._peer_refresh_timer.timeout.connect(self._refresh_peers_and_suggestions)
        self._peer_refresh_timer.start()
        
        self._cleanup_timer = QTimer()
        self._cleanup_timer.setInterval(300000)
        self._cleanup_timer.timeout.connect(self._cleanup_offline_peers)
        self._cleanup_timer.start()
    
    def stop(self):
        if self._peer_refresh_timer:
            self._peer_refresh_timer.stop()
        if self._cleanup_timer:
            self._cleanup_timer.stop()
        if self._suggestions_debounce_timer:
            self._suggestions_debounce_timer.stop()
        self.chat_core.stop()
    
    def _refresh_peers_and_suggestions(self):
        self._update_peers_from_core()
        self._refresh_suggestions(debounced=True)
    
    def _update_peers_from_core(self):
        peers = self.chat_core.get_known_peers()
        self.peers = {peer["peer_id"]: peer for peer in peers}
        self._refresh_chat_list()
        self._refresh_suggestions()
    
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
    
    def _get_suggestions(self) -> List[Dict]:
        suggestions = []
        known_peer_ids = set(self.peers.keys())
        
        known_peers_from_core = self.chat_core.get_known_peers()
        for peer in known_peers_from_core:
            known_peer_ids.add(peer["peer_id"])
        
        temp_peers = self.chat_core.get_temp_discovered_peers()
        added_peer_ids = set()
        
        now = time.time()
        for peer in temp_peers:
            peer_id = peer.get("peer_id") or peer.get("peer_id", "")
            
            if not peer_id:
                continue
            
            if peer_id in known_peer_ids:
                continue
            
            if peer_id in self.pending_friend_requests:
                continue
            
            if peer_id in added_peer_ids:
                continue
            
            last_seen = peer.get("last_seen", 0)
            is_online = (now - last_seen) < 15
            
            # Only show online peers in suggestions
            if not is_online:
                continue
            
            suggestions.append({
                "peer_id": peer_id,
                "name": peer.get("display_name", "Unknown"),
                "status_text": "Online",
                "is_added": False,
            })
            added_peer_ids.add(peer_id)
        
        return suggestions
    
    def _refresh_chat_list(self):
        conversations = self._get_conversations()
        self.chat_list_updated.emit(conversations)
    
    def _refresh_suggestions(self, debounced: bool = False):
        if not debounced:
            self._suggestions_pending_refresh = True
            if self._suggestions_debounce_timer and not self._suggestions_debounce_timer.isActive():
                self._suggestions_debounce_timer.start()
            return
        
        self._suggestions_pending_refresh = False
        log.debug("Refreshing suggestions list")
        suggestions = self._get_suggestions()
        self.suggestions_updated.emit(suggestions)
    
    def on_chat_selected(self, chat_id: str, chat_name: str):
        if not chat_id:
            return
        self.current_peer_id = chat_id
        self.unread_counts[chat_id] = 0
        history = self.chat_core.get_message_history(chat_id)
        self.load_chat_history.emit(chat_id, history)
        self._refresh_chat_list()
    
    def on_suggestion_add_requested(self, peer_id: str, peer_name: str):
        try:
            log.info(f"Adding user requested for: {peer_name} ({peer_id})")
            
            if not peer_id:
                self.show_message_box.emit("warning", "Friend Request", "Invalid peer ID.")
                return
            
            self.pending_friend_requests[peer_id] = peer_name
            
            success = self.chat_core.send_friend_request(peer_id)
            log.info(f"Friend request result for {peer_id}: {success}")
            
            if success:
                self._remove_peer_from_suggestions(peer_id)
                self._refresh_suggestions(debounced=True)
                self.show_message_box.emit("info", "Friend Request", f"Friend request sent to {peer_name}! They will receive a notification to accept or reject.")
            else:
                self.pending_friend_requests.pop(peer_id, None)
                
                peer_info = None
                if hasattr(self.chat_core, 'router') and hasattr(self.chat_core.router, 'temp_discovered_peers'):
                    peer_info = self.chat_core.router.temp_discovered_peers.get(peer_id)
                
                error_msg = f"Failed to send friend request to {peer_name}."
                if peer_info:
                    error_msg += f"\nDetails: IP={peer_info.ip}, Port={peer_info.tcp_port}"
                    if peer_info.tcp_port == 0:
                        error_msg += "\n(Peer not fully discovered yet, please wait)"
                
                self.show_message_box.emit("warning", "Friend Request", f"{error_msg}\nPeer may be offline or invalid.")
        except Exception as e:
            import traceback
            self.show_message_box.emit("error", "Error", f"An error occurred: {e}")
    
    def on_suggestion_chat_requested(self, peer_id: str, peer_name: str):
        self.current_peer_id = peer_id
        self.unread_counts[peer_id] = 0
        history = self.chat_core.get_message_history(peer_id)
        self.load_chat_history.emit(peer_id, history)
        self._refresh_chat_list()
        self._refresh_suggestions(debounced=True)
    
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
                success = self.chat_core.send_message(
                    self.current_peer_id,
                    message_text,
                    msg_type="text",
                    file_name=None,
                    file_data=None,
                    audio_data=None
                )
                if success:
                    success_count += 1
            except Exception as e:
                pass
        
        if preview_items:
            self._preview_items = {}
            if hasattr(self, 'clear_preview_callback'):
                self.clear_preview_callback()
        
        if success_count == 0 and total_items > 0:
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
                self.peers[peer_id] = peer_info
                self._refresh_chat_list()
        except Exception as e:
            import traceback
    
    def _on_temp_peer_updated_signal(self, peer_info: Dict):
        try:
            self._refresh_suggestions(debounced=False)
        except Exception as e:
            import traceback
    
    def _on_temp_peer_removed_signal(self, peer_id: str):
        try:
            self._remove_peer_from_suggestions(peer_id)
        except Exception as e:
            import traceback
    
    def _remove_peer_from_suggestions(self, peer_id: str):
        if not peer_id:
            return
        
        self.chat_core.remove_temp_peer(peer_id)
        self._refresh_suggestions(debounced=True)
    
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
            self._remove_peer_from_suggestions(peer_id)
            
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
            
            self._remove_peer_from_suggestions(peer_id)
            
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
            temp_peers = self.chat_core.get_temp_discovered_peers()
            for peer in temp_peers:
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
    

