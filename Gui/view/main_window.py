from collections import defaultdict
from typing import Dict, List
import logging

from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QSplitter, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer, QObject, Signal

from Core.core_api import ChatCore
from .chat_list import ChatList
from .chat_area import ChatArea
from .notifications_panel import NotificationsPanel

log = logging.getLogger(__name__)

class MainWindow(QMainWindow):

    def __init__(self, user_name: str = "User", user_id: str = None, username: str = None, port: int = 5555, avatar_path: str = None, tcp_port: int = 55000):
        super().__init__()
        self.setWindowTitle(f"Chat P2P - {user_name}")
        self.setGeometry(100, 100, 1500, 900)
        self.setMinimumSize(800, 600)

        self.user_name = user_name
        self.user_id = user_id or ""
        self.username = username or user_name
        self.avatar_path = avatar_path
        self.tcp_port = tcp_port

        self.left_sidebar = None
        self.center_panel = None
        self.right_sidebar = None

        from app.user_manager import _normalize_username
        normalized_username = _normalize_username(self.username)
        
        self.chat_core = ChatCore(
            username=normalized_username,
            display_name=self.user_name,
            tcp_port=self.tcp_port,
            on_message_callback=None,  # Use signals instead
            on_peer_update=None,  # Use signals instead
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

        self._setup_ui()
        self._setup_component_signals()
        self._start_chat_core()

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

        self.left_sidebar = ChatList(user_name=self.user_name, avatar_path=self.avatar_path)
        self.center_panel = ChatArea()
        self.right_sidebar = NotificationsPanel()

        splitter_right = QSplitter(Qt.Horizontal)
        splitter_right.addWidget(self.center_panel)
        splitter_right.addWidget(self.right_sidebar)
        splitter_right.setStretchFactor(0, 3)
        splitter_right.setStretchFactor(1, 1)

        splitter_main = QSplitter(Qt.Horizontal)
        splitter_main.addWidget(self.left_sidebar)
        splitter_main.addWidget(splitter_right)
        splitter_main.setStretchFactor(0, 1)
        splitter_main.setStretchFactor(1, 4)

        main_layout.addWidget(splitter_main)
        splitter_main.setSizes([325, 1000])

    def _setup_component_signals(self):
        chat_list_controller = self.left_sidebar.get_controller()
        chat_list_controller.set_peer_refresh_handler(self._update_peers_from_core)
        self.left_sidebar.connect_chat_selected(self._on_chat_selected)

        chat_area_controller = self.center_panel.get_controller()
        chat_area_controller.set_send_handler(self._send_message_from_controller)
        self.center_panel.connect_file_attached(self._handle_file_attached)

        self.right_sidebar.suggestion_add_requested.connect(self._on_suggestion_add_requested)
        self.right_sidebar.suggestion_chat_requested.connect(self._on_suggestion_chat_requested)
        
        self.pending_friend_requests: Dict[str, str] = {}
        
        self._active_request_dialogs: Dict[str, QDialog] = {}

    def _start_chat_core(self):
        try:
            self.chat_core.start()
        except Exception as exc:
            QMessageBox.critical(self, "ChatCore Error", f"Failed to start chat core: {exc}")
            raise

        self._suggestions_debounce_timer = QTimer(self)
        self._suggestions_debounce_timer.setSingleShot(True)  # Only fire once
        self._suggestions_debounce_timer.setInterval(2000)  # Wait 2 seconds before refreshing
        self._suggestions_debounce_timer.timeout.connect(lambda: self._refresh_suggestions(debounced=True))
        self._suggestions_pending_refresh = False

        self._update_peers_from_core()
        self._refresh_chat_list()
        self._refresh_suggestions()

        self._peer_refresh_timer = QTimer(self)
        self._peer_refresh_timer.setInterval(5000)  # Refresh peer list mỗi 5 giây
        self._peer_refresh_timer.timeout.connect(self._refresh_peers_and_suggestions)
        self._peer_refresh_timer.start()
        
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.setInterval(300000)  # 5 minutes
        self._cleanup_timer.timeout.connect(self._cleanup_offline_peers)
        self._cleanup_timer.start()
    
    def _refresh_peers_and_suggestions(self):
        
        self._update_peers_from_core()
        self._refresh_suggestions(debounced=True)  # Force immediate refresh for timer-based updates

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
                other_peer_id = msg.get("peer_id")  # Already set by core_api
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
                    log.info("Rebuilt peer %s from messages.json (not in peers.json)", peer_id)
        
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
        
        import time
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
            is_online = (now - last_seen) < 15  # Consider online if seen within last 15 seconds
            
            suggestions.append({
                "peer_id": peer_id,  # Always use peer_id as key
                "name": peer.get("display_name", "Unknown"),
                "status_text": "Online" if is_online else "Offline",
                "is_added": False,  # Not yet added - show Add button
            })
            added_peer_ids.add(peer_id)
        
        return suggestions

    def _load_history_to_center(self, peer_id: str):
        history = self.chat_core.get_message_history(peer_id)
        self.center_panel.load_chat_history(history)

    def _refresh_chat_list(self):
        self.left_sidebar.load_conversations(self._get_conversations())

    def _refresh_suggestions(self, debounced: bool = False):
        
        if not debounced:
            self._suggestions_pending_refresh = True
            if not self._suggestions_debounce_timer.isActive():
                self._suggestions_debounce_timer.start()
            return
        
        self._suggestions_pending_refresh = False
        log.debug("Refreshing suggestions list")
        self.right_sidebar.load_suggestions(self._get_suggestions())

    def _on_chat_selected(self, chat_id: str, chat_name: str):
        if not chat_id:
            return
        self.current_peer_id = chat_id
        self.unread_counts[chat_id] = 0
        self._load_history_to_center(chat_id)
        self._refresh_chat_list()

    def _on_suggestion_add_requested(self, peer_id: str, peer_name: str):
        
        try:
            log.info(f"Adding user requested for: {peer_name} ({peer_id})")
            
            if not peer_id:
                QMessageBox.warning(self, "Friend Request", "Invalid peer ID.")
                return
            
            self.pending_friend_requests[peer_id] = peer_name
            
            success = self.chat_core.send_friend_request(peer_id)
            log.info(f"Friend request result for {peer_id}: {success}")
            
            if success:
                self._remove_peer_from_suggestions(peer_id)
                self._refresh_suggestions(debounced=True)
                QMessageBox.information(self, "Friend Request", f"Friend request sent to {peer_name}! They will receive a notification to accept or reject.")
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
                
                QMessageBox.warning(self, "Friend Request", f"{error_msg}\nPeer may be offline or invalid.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
    
    def _on_suggestion_chat_requested(self, peer_id: str, peer_name: str):
        
        self.current_peer_id = peer_id
        self.unread_counts[peer_id] = 0
        self._load_history_to_center(peer_id)
        self._refresh_chat_list()
        self._refresh_suggestions(debounced=True)  # Force immediate refresh when opening chat

    def _send_message_from_controller(self, message_text: str) -> bool:
        if not self.current_peer_id:
            QMessageBox.information(self, "Select chat", "Please choose a conversation before sending messages.")
            return False
        success = self.chat_core.send_message(self.current_peer_id, message_text)
        if not success:
            QMessageBox.warning(self, "Network error", "Failed to send message. Peer might be offline.")
        return success

    def _handle_file_attached(self, file_path: str, file_name: str):
        note = f"📎 Sent file: {file_name}"
        self._send_message_from_controller(note)

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
            
            if peer_id == self.current_peer_id and self.center_panel:
                self.center_panel.add_message(content, is_sender, time_str=time_str)
            
            self._refresh_chat_list()
        except Exception as e:
            import traceback
            print(f"Error in _on_message_received_signal: {e}")
            traceback.print_exc()

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
        
        if self.right_sidebar:
            self.right_sidebar.remove_suggestion(peer_id)
        
        self.chat_core.remove_temp_peer(peer_id)
        
        self._refresh_suggestions(debounced=True)
    
    def _on_friend_request_received_signal(self, peer_id: str, display_name: str):
        
        try:
            log.info("Friend request signal received for %s (%s)", display_name, peer_id)
            
            if peer_id in self.peers:
                log.debug("Ignoring friend request from %s: already a friend", peer_id)
                return
            
            if peer_id in self.pending_friend_requests:
                log.debug("Ignoring duplicate friend request from %s: already in pending_friend_requests", peer_id)
                return
            
            if peer_id in self._active_request_dialogs:
                existing_dialog = self._active_request_dialogs.get(peer_id)
                if existing_dialog and existing_dialog.isVisible():
                    log.debug("Ignoring friend request from %s: dialog already visible", peer_id)
                    return
                log.debug("Removing stale dialog reference for %s", peer_id)
                del self._active_request_dialogs[peer_id]
            
            self.pending_friend_requests[peer_id] = display_name
            log.info("Showing friend request dialog for %s (%s)", display_name, peer_id)
            
            self._show_friend_request_dialog(peer_id, display_name)
        except Exception as e:
            import traceback
            log.error(f"Error in _on_friend_request_received_signal: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error processing friend request: {e}")
    
    def _show_friend_request_dialog(self, peer_id: str, display_name: str):
        
        if peer_id in self._active_request_dialogs:
            existing_dialog = self._active_request_dialogs[peer_id]
            if existing_dialog and existing_dialog.isVisible():
                log.warning("Dialog already exists and visible for %s, skipping", peer_id)
                return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Friend Request")
        dialog.setModal(True)
        dialog.setFixedSize(400, 200)
        
        self._active_request_dialogs[peer_id] = dialog
        log.debug("Created friend request dialog for %s (%s)", display_name, peer_id)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        message_label = QLabel(f"<b>{display_name}</b> wants to be your friend.")
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(message_label)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        accept_btn = QPushButton("Accept")
        accept_btn.setObjectName("ModernPrimaryButton")
        accept_btn.setFixedHeight(40)
        accept_btn.clicked.connect(lambda: self._on_accept_friend_request(dialog, peer_id))
        
        reject_btn = QPushButton("Reject")
        reject_btn.setStyleSheet()
        reject_btn.setFixedHeight(40)
        reject_btn.clicked.connect(lambda: self._on_reject_friend_request(dialog, peer_id))
        
        button_layout.addWidget(accept_btn)
        button_layout.addWidget(reject_btn)
        layout.addLayout(button_layout)
        
        def cleanup_dialog():
            if peer_id in self._active_request_dialogs:
                del self._active_request_dialogs[peer_id]
        
        dialog.finished.connect(lambda result: cleanup_dialog())
        
        dialog.exec()
    
    def _on_accept_friend_request(self, dialog: QDialog, peer_id: str):
        
        if peer_id in self._active_request_dialogs:
            del self._active_request_dialogs[peer_id]
        
        dialog.accept()
        display_name = self.pending_friend_requests.pop(peer_id, "Unknown")
        
        success = self.chat_core.accept_friend(peer_id)
        if success:
            self._update_peers_from_core()
            self._refresh_chat_list()
            self._remove_peer_from_suggestions(peer_id)
            
            self.current_peer_id = peer_id
            self.unread_counts[peer_id] = 0
            self._load_history_to_center(peer_id)
            self._refresh_chat_list()
            
            QMessageBox.information(self, "Friend Added", f"You are now friends with {display_name}! Chat window opened.")
        else:
            QMessageBox.warning(self, "Error", f"Failed to accept friend request from {display_name}.")
    
    def _on_reject_friend_request(self, dialog: QDialog, peer_id: str):
        
        if peer_id in self._active_request_dialogs:
            del self._active_request_dialogs[peer_id]
        
        dialog.reject()
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
            self._load_history_to_center(peer_id)
            self._refresh_chat_list()
            
            QMessageBox.information(self, "Friend Request Accepted", f"{peer_name} accepted your friend request! Chat window opened.")
        except Exception as e:
            import traceback
            log.error(f"Error in _on_friend_accepted_signal: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error processing friend accept: {e}")
    
    def _on_friend_rejected_signal(self, peer_id: str):
        
        try:
            peer_name = "Unknown"
            temp_peers = self.chat_core.get_temp_discovered_peers()
            for peer in temp_peers:
                if peer["peer_id"] == peer_id:
                    peer_name = peer.get("display_name", "Unknown")
                    break
            
            QMessageBox.warning(self, "Friend Request Rejected", f"{peer_name} rejected your friend request.")
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
    
    def closeEvent(self, event):
        if hasattr(self, "_peer_refresh_timer"):
            self._peer_refresh_timer.stop()
        self.chat_core.stop()
        event.accept()
