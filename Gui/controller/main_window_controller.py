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
        self._pending_audios = {}
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
        known_peer_ids = set(self.peers.keys())
        all_history = self.chat_core.get_message_history()
        
        peer_ids_from_messages = set()
        for msg in all_history:
            if msg.get("sender_id") == self.chat_core.peer_id:
                other_peer_id = msg.get("peer_id")
            else:
                other_peer_id = msg.get("sender_id")
            
            if other_peer_id and other_peer_id != self.chat_core.peer_id:
                peer_ids_from_messages.add(other_peer_id)
        
        for peer_id in peer_ids_from_messages:
            if peer_id not in known_peer_ids:
                peer_messages = [m for m in all_history if m.get("peer_id") == peer_id or m.get("sender_id") == peer_id]
                if peer_messages:
                    last_msg = peer_messages[-1]
                    self.peers[peer_id] = {
                        "peer_id": peer_id,
                        "display_name": last_msg.get("sender_name", "Unknown"),
                        "status": "unknown",
                        "ip": "",
                        "tcp_port": 0,
                    }
                    log.info("Rebuilt peer %s from messages.json", peer_id)
        
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
            
            suggestions.append({
                "peer_id": peer_id,
                "name": peer.get("display_name", "Unknown"),
                "status_text": "Online" if is_online else "Offline",
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
            traceback.print_exc()
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
        
        file_name = None
        file_data = None
        audio_data = None
        
        for note, (fname, fdata) in self._pending_files.items():
            if note in message_text:
                file_name = fname
                file_data = fdata
                message_text = message_text.replace(note, "").strip()
                break
        
        for note, adata in self._pending_audios.items():
            if note in message_text:
                audio_data = adata
                message_text = message_text.replace(note, "").strip()
                break
        
        if not message_text and not file_name and not audio_data:
            return False
        
        if not message_text:
            if file_name:
                message_text = f"📎{file_name}"
            elif audio_data:
                message_text = "🎤 Audio"
        
        success = self.chat_core.send_message(
            self.current_peer_id,
            message_text,
            file_name=file_name,
            file_data=file_data,
            audio_data=audio_data
        )
        
        if file_name:
            self._pending_files.pop(f"📎{file_name}", None)
        if audio_data:
            self._pending_audios.pop(f"🎤 Audio", None)
        
        if not success:
            self.show_message_box.emit("warning", "Network error", "Failed to send message. Peer might be offline.")
        return success
    
    def handle_file_attached(self, file_path: str, file_name: str, file_data_base64: str):
        note = f"📎{file_name}"
        self._pending_files[note] = (file_name, file_data_base64)
    
    def handle_audio_recorded(self, audio_path: str, audio_data_base64: str):
        note = "🎤 Audio"
        self._pending_audios[note] = audio_data_base64
    
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
            
            if peer_id == self.current_peer_id:
                file_name = payload.get("file_name")
                file_data = payload.get("file_data")
                audio_data = payload.get("audio_data")
                
                display_content = content
                if file_name:
                    display_content = f"📎 {file_name}\n{content}" if content else f"📎 {file_name}"
                elif audio_data:
                    display_content = f"🎤 Audio\n{content}" if content else "🎤 Audio"
                
                payload["display_content"] = display_content
                
                if file_name and file_data:
                    self._save_received_file(peer_id, file_name, file_data)
                if audio_data:
                    self._save_received_audio(peer_id, audio_data)
            
            self.message_received.emit(payload)
            self._refresh_chat_list()
        except Exception as e:
            import traceback
            print(f"Error in _on_message_received_signal: {e}")
            traceback.print_exc()
    
    def _get_peer_folder_name(self, peer_id: str) -> str:
        from app.user_manager import _normalize_username
        
        if peer_id in self.peers:
            peer_info = self.peers[peer_id]
            display_name = peer_info.get("display_name", peer_id)
            return _normalize_username(display_name)
        
        return _normalize_username(peer_id[:8])
    
    def _save_received_file(self, peer_id: str, file_name: str, file_data_base64: str):
        try:
            peer_folder_name = self._get_peer_folder_name(peer_id)
            peer_dir = os.path.join("data", peer_folder_name)
            files_dir = os.path.join(peer_dir, "files")
            os.makedirs(files_dir, exist_ok=True)
            
            file_path = os.path.join(files_dir, file_name)
            counter = 1
            while os.path.exists(file_path):
                name, ext = os.path.splitext(file_name)
                file_path = os.path.join(files_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            file_data = base64.b64decode(file_data_base64)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            print(f"File saved to peer folder: {file_path}")
        except Exception as e:
            print(f"Error saving file: {e}")
    
    def _save_received_audio(self, peer_id: str, audio_data_base64: str):
        try:
            peer_folder_name = self._get_peer_folder_name(peer_id)
            peer_dir = os.path.join("data", peer_folder_name)
            audios_dir = os.path.join(peer_dir, "audios")
            os.makedirs(audios_dir, exist_ok=True)
            
            audio_file = f"audio_{int(time.time())}.wav"
            file_path = os.path.join(audios_dir, audio_file)
            
            counter = 1
            while os.path.exists(file_path):
                audio_file = f"audio_{int(time.time())}_{counter}.wav"
                file_path = os.path.join(audios_dir, audio_file)
                counter += 1
            
            audio_data = base64.b64decode(audio_data_base64)
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            
            print(f"Audio saved to peer folder: {file_path}")
        except Exception as e:
            print(f"Error saving audio: {e}")
    
    def _on_peer_updated_signal(self, peer_info: Dict):
        try:
            peer_id = peer_info.get("peer_id", "")
            if peer_id:
                self.peers[peer_id] = peer_info
                self._refresh_chat_list()
        except Exception as e:
            import traceback
            print(f"Error in _on_peer_updated_signal: {e}")
            traceback.print_exc()
    
    def _on_temp_peer_updated_signal(self, peer_info: Dict):
        try:
            self._refresh_suggestions(debounced=False)
        except Exception as e:
            import traceback
            print(f"Error in _on_temp_peer_updated_signal: {e}")
            traceback.print_exc()
    
    def _on_temp_peer_removed_signal(self, peer_id: str):
        try:
            self._remove_peer_from_suggestions(peer_id)
        except Exception as e:
            import traceback
            print(f"Error in _on_temp_peer_removed_signal: {e}")
            traceback.print_exc()
    
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
            traceback.print_exc()
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
            traceback.print_exc()
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
            print(f"Error in _on_friend_rejected_signal: {e}")
            traceback.print_exc()
    
    def _cleanup_offline_peers(self):
        if self.chat_core:
            removed_count = self.chat_core.cleanup_offline_peers()
            if removed_count > 0:
                log.info("Cleaned up %s offline peers", removed_count)
                self._refresh_chat_list()
    

