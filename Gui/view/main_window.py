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
    """Main application window bound to the real ChatCore backend."""

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

        # Import normalize function
        from app.user_manager import _normalize_username
        normalized_username = _normalize_username(self.username)
        
        # Create ChatCore WITHOUT callbacks - we'll use Qt Signals instead
        self.chat_core = ChatCore(
            username=normalized_username,
            display_name=self.user_name,
            tcp_port=self.tcp_port,
            on_message_callback=None,  # Use signals instead
            on_peer_update=None,  # Use signals instead
        )
        
        # Connect Qt Signals for thread-safe communication from Core to GUI
        # All signals are automatically queued to main thread
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

    # ------------------------------------------------------------------ #
    # UI setup
    # ------------------------------------------------------------------ #
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
        
        # Store pending friend requests (peer_id -> display_name)
        self.pending_friend_requests: Dict[str, str] = {}
        
        # Track active friend request dialogs to prevent duplicates
        self._active_request_dialogs: Dict[str, QDialog] = {}

    # ------------------------------------------------------------------ #
    # Core lifecycle
    # ------------------------------------------------------------------ #
    def _start_chat_core(self):
        try:
            self.chat_core.start()
        except Exception as exc:
            QMessageBox.critical(self, "ChatCore Error", f"Failed to start chat core: {exc}")
            raise

        # Initialize debounce timer for suggestions refresh BEFORE it's used
        # Debounce timer for suggestions refresh (prevent too frequent updates)
        self._suggestions_debounce_timer = QTimer(self)
        self._suggestions_debounce_timer.setSingleShot(True)  # Only fire once
        self._suggestions_debounce_timer.setInterval(2000)  # Wait 2 seconds before refreshing
        self._suggestions_debounce_timer.timeout.connect(lambda: self._refresh_suggestions(debounced=True))
        self._suggestions_pending_refresh = False

        self._update_peers_from_core()
        self._refresh_chat_list()
        self._refresh_suggestions()

        # Timer chỉ để refresh peer list và suggestions định kỳ (không phải để nhận messages)
        # Messages đã được xử lý realtime qua callback chain
        self._peer_refresh_timer = QTimer(self)
        self._peer_refresh_timer.setInterval(5000)  # Refresh peer list mỗi 5 giây
        self._peer_refresh_timer.timeout.connect(self._refresh_peers_and_suggestions)
        self._peer_refresh_timer.start()
        
        # Cleanup offline peers every 5 minutes
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.setInterval(300000)  # 5 minutes
        self._cleanup_timer.timeout.connect(self._cleanup_offline_peers)
        self._cleanup_timer.start()
    
    def _refresh_peers_and_suggestions(self):
        """Refresh both peers and suggestions lists"""
        self._update_peers_from_core()
        self._refresh_suggestions(debounced=True)  # Force immediate refresh for timer-based updates

    # ------------------------------------------------------------------ #
    # Data helpers
    # ------------------------------------------------------------------ #
    def _update_peers_from_core(self):
        peers = self.chat_core.get_known_peers()
        self.peers = {peer["peer_id"]: peer for peer in peers}
        self._refresh_chat_list()
        self._refresh_suggestions()

    def _get_conversations(self) -> List[Dict]:
        """
        Get conversations list.
        CRITICAL: Rebuild peers from messages.json if they're not in peers.json.
        This ensures mutual friendship - if we have messages with a peer,
        they should appear in chat list even if not in peers.json yet.
        """
        conversations = []
        
        # First, get all peers from peers.json
        known_peer_ids = set(self.peers.keys())
        
        # Get all message history to find peers we've chatted with
        all_history = self.chat_core.get_message_history()
        
        # Build set of peer_ids from messages
        peer_ids_from_messages = set()
        for msg in all_history:
            # Determine the other peer in the conversation
            if msg.get("sender_id") == self.chat_core.peer_id:
                other_peer_id = msg.get("peer_id")  # Already set by core_api
            else:
                other_peer_id = msg.get("sender_id")
            
            if other_peer_id and other_peer_id != self.chat_core.peer_id:
                peer_ids_from_messages.add(other_peer_id)
        
        # For peers in messages but not in peers.json, create temporary peer entries
        for peer_id in peer_ids_from_messages:
            if peer_id not in known_peer_ids:
                # Rebuild peer from messages
                peer_messages = [m for m in all_history if m.get("peer_id") == peer_id or m.get("sender_id") == peer_id]
                if peer_messages:
                    last_msg = peer_messages[-1]
                    # Create temporary peer entry
                    self.peers[peer_id] = {
                        "peer_id": peer_id,
                        "display_name": last_msg.get("sender_name", "Unknown"),
                        "status": "unknown",
                        "ip": "",
                        "tcp_port": 0,
                    }
                    log.info("Rebuilt peer %s from messages.json (not in peers.json)", peer_id)
        
        # Now build conversations from all peers (including rebuilt ones)
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
        """
        Get suggestions list:
        Only show temp discovered peers (not yet added to friends).
        Do NOT show peers that are already friends, pending requests, or have active dialogs.
        This ensures friends never appear in suggestions, even after restart.
        Uses peer_id for all filtering (not display_name) to prevent mismatches.
        """
        suggestions = []
        
        # Get all friend IDs from current peers dict (loaded from peers.json)
        known_peer_ids = set(self.peers.keys())
        
        # Also get from Core to ensure we have the latest list
        known_peers_from_core = self.chat_core.get_known_peers()
        for peer in known_peers_from_core:
            known_peer_ids.add(peer["peer_id"])
        
        # Get temp discovered peers (not yet added to friends)
        # MessageRouter.get_temp_discovered_peers() already filters out friends and pending requests,
        # but we double-check here for safety
        temp_peers = self.chat_core.get_temp_discovered_peers()
        
        # Track added peer_ids to prevent duplicates
        added_peer_ids = set()
        
        for peer in temp_peers:
            peer_id = peer.get("peer_id") or peer.get("peer_id", "")
            
            # Skip if peer_id is empty
            if not peer_id:
                continue
            
            # Skip if already a friend (double-check for safety)
            if peer_id in known_peer_ids:
                continue
            
            # Skip if pending friend request (we sent request, waiting for response)
            if peer_id in self.pending_friend_requests:
                continue
            
            # Skip if already added to suggestions (prevent duplicates)
            if peer_id in added_peer_ids:
                continue
            
            # Add to suggestions
            suggestions.append({
                "peer_id": peer_id,  # Always use peer_id as key
                "name": peer.get("display_name", "Unknown"),
                "status_text": "Online" if peer.get("status") == "online" else "Offline",
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
        """
        Refresh suggestions list.
        If debounced=False, schedules a debounced refresh.
        If debounced=True, actually performs the refresh.
        """
        if not debounced:
            # Schedule debounced refresh
            self._suggestions_pending_refresh = True
            if not self._suggestions_debounce_timer.isActive():
                self._suggestions_debounce_timer.start()
            return
        
        # Actually perform refresh
        self._suggestions_pending_refresh = False
        log.debug("Refreshing suggestions list")
        self.right_sidebar.load_suggestions(self._get_suggestions())

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #
    def _on_chat_selected(self, chat_id: str, chat_name: str):
        if not chat_id:
            return
        self.current_peer_id = chat_id
        self.unread_counts[chat_id] = 0
        self._load_history_to_center(chat_id)
        self._refresh_chat_list()

    def _on_suggestion_add_requested(self, peer_id: str, peer_name: str):
        """
        Handle when user clicks Add button on a suggestion.
        Sends a FRIEND_REQUEST to the peer so they can accept/reject.
        After sending, remove peer from suggestions immediately and track as pending.
        Once the peer accepts, they will be added to friends list automatically.
        """
        try:
            print(f"[DEBUG] MainWindow._on_suggestion_add_requested called: {peer_name} ({peer_id})")
            log.info(f"Adding user requested for: {peer_name} ({peer_id})")
            
            if not peer_id:
                print("[DEBUG] Invalid peer_id")
                QMessageBox.warning(self, "Friend Request", "Invalid peer ID.")
                return
            
            # Mark as pending request (so it won't appear in suggestions)
            self.pending_friend_requests[peer_id] = peer_name
            print(f"[DEBUG] Marked as pending: {peer_id}")
            
            # Send friend request to the peer
            print(f"[DEBUG] Calling send_friend_request for {peer_id}...")
            success = self.chat_core.send_friend_request(peer_id)
            print(f"[DEBUG] Friend request result for {peer_id}: {success}")
            log.info(f"Friend request result for {peer_id}: {success}")
            
            if success:
                print(f"[DEBUG] Request sent successfully, removing from suggestions")
                # Remove peer from suggestions immediately (user has sent request)
                # MessageRouter will add to _outgoing_requests, so it won't appear in suggestions
                self._remove_peer_from_suggestions(peer_id)
                # Force immediate refresh of suggestions to update UI
                self._refresh_suggestions(debounced=True)
                QMessageBox.information(self, "Friend Request", f"Friend request sent to {peer_name}! They will receive a notification to accept or reject.")
            else:
                print(f"[DEBUG] Request failed, showing error")
                # Remove from pending if send failed
                self.pending_friend_requests.pop(peer_id, None)
                
                # Check why it failed
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
            print(f"[ERROR] Exception in _on_suggestion_add_requested: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
    
    def _on_suggestion_chat_requested(self, peer_id: str, peer_name: str):
        """
        Handle when user clicks on a suggestion that's already added.
        Opens chat with that peer.
        """
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

    # ------------------------------------------------------------------ #
    # Qt Signal handlers - Called in main thread (thread-safe)
    # These are connected to ChatCore.signals and run in main thread
    # ------------------------------------------------------------------ #
    def _on_message_received_signal(self, payload: Dict):
        """
        Handle message received signal (runs in main thread).
        This is connected to chat_core.signals.message_received.
        """
        try:
            # This runs in main thread - safe to update UI
            peer_id = payload.get("peer_id", "")
            sender_name = payload.get("sender_name", "Unknown")
            content = payload.get("content", "")
            is_sender = payload.get("is_sender", False)
            timestamp = payload.get("timestamp", 0)
            time_str = payload.get("time_str", "")
            
            # Update unread count if not sender and not current chat
            if not is_sender and peer_id != self.current_peer_id:
                self.unread_counts[peer_id] = self.unread_counts.get(peer_id, 0) + 1
            
            # If this is the current chat, add message to chat area
            if peer_id == self.current_peer_id and self.center_panel:
                self.center_panel.add_message(content, is_sender, time_str=time_str)
            
            # Refresh chat list to update unread counts
            self._refresh_chat_list()
        except Exception as e:
            import traceback
            print(f"Error in _on_message_received_signal: {e}")
            traceback.print_exc()

    def _on_peer_updated_signal(self, peer_info: Dict):
        """
        Handle peer updated signal (runs in main thread).
        This is connected to chat_core.signals.peer_updated.
        """
        try:
            # This runs in main thread - safe to update UI
            peer_id = peer_info.get("peer_id", "")
            if peer_id:
                self.peers[peer_id] = peer_info
                self._refresh_chat_list()
        except Exception as e:
            import traceback
            print(f"Error in _on_peer_updated_signal: {e}")
            traceback.print_exc()
    
    def _on_temp_peer_updated_signal(self, peer_info: Dict):
        """
        Handle temporary peer updated signal (runs in main thread).
        This is connected to chat_core.signals.temp_peer_updated.
        Called when discovery finds a new peer (not yet added).
        """
        try:
            # This runs in main thread - safe to update UI
            # Use debounced refresh to prevent too frequent updates
            self._refresh_suggestions(debounced=False)
        except Exception as e:
            import traceback
            print(f"Error in _on_temp_peer_updated_signal: {e}")
            traceback.print_exc()
    
    def _on_temp_peer_removed_signal(self, peer_id: str):
        """
        Handle temporary peer removed signal (runs in main thread).
        This is connected to chat_core.signals.temp_peer_removed.
        Called when a peer is removed from suggestions (became friend).
        """
        try:
            # This runs in main thread - safe to update UI
            # Remove peer from suggestions immediately
            self._remove_peer_from_suggestions(peer_id)
        except Exception as e:
            import traceback
            print(f"Error in _on_temp_peer_removed_signal: {e}")
            traceback.print_exc()
    
    def _remove_peer_from_suggestions(self, peer_id: str):
        """
        Remove a peer from suggestions list immediately.
        This is called when peer becomes a friend or request is sent.
        Uses peer_id (not display_name) to ensure correct removal.
        """
        if not peer_id:
            return
        
        # Remove from NotificationsPanel directly (immediate UI update)
        if self.right_sidebar:
            self.right_sidebar.remove_suggestion(peer_id)
        
        # Remove from temp_discovered_peers in Core (if not already removed)
        # This ensures the peer won't appear in suggestions after refresh
        self.chat_core.remove_temp_peer(peer_id)
        
        # Refresh suggestions - the peer will be filtered out by _get_suggestions()
        # which checks known_peer_ids and temp_discovered_peers
        # Force immediate refresh (no debounce) when removing peer
        self._refresh_suggestions(debounced=True)
    
    def _on_friend_request_received_signal(self, peer_id: str, display_name: str):
        """
        Handle friend request received signal (runs in main thread).
        This is connected to chat_core.signals.friend_request_received.
        Show popup dialog for user to Accept/Reject.
        Only shows dialog once per peer_id to prevent duplicate popups.
        """
        try:
            # This runs in main thread - safe to show dialog
            print(f"[DEBUG] Friend request signal received for {display_name} ({peer_id})")
            log.info("Friend request signal received for %s (%s)", display_name, peer_id)
            
            # Check if already a friend - ignore
            if peer_id in self.peers:
                print(f"[DEBUG] Ignoring: {peer_id} already a friend")
                log.debug("Ignoring friend request from %s: already a friend", peer_id)
                return
            
            print(f"[DEBUG] Not a friend, checking pending requests...")
            # Check if already have pending request for this peer - ignore duplicate
            if peer_id in self.pending_friend_requests:
                print(f"[DEBUG] Ignoring: {peer_id} already in pending_friend_requests")
                log.debug("Ignoring duplicate friend request from %s: already in pending_friend_requests", peer_id)
                return
            
            print(f"[DEBUG] Not pending, checking active dialogs...")
            # Check if dialog already active for this peer - don't create duplicate
            if peer_id in self._active_request_dialogs:
                existing_dialog = self._active_request_dialogs.get(peer_id)
                if existing_dialog and existing_dialog.isVisible():
                    print(f"[DEBUG] Ignoring: dialog already visible for {peer_id}")
                    log.debug("Ignoring friend request from %s: dialog already visible", peer_id)
                    return
                # Dialog exists but not visible - remove from tracking
                print(f"[DEBUG] Removing stale dialog reference for {peer_id}")
                log.debug("Removing stale dialog reference for %s", peer_id)
                del self._active_request_dialogs[peer_id]
            
            # Store pending request
            print(f"[DEBUG] Storing pending request and showing dialog for {display_name} ({peer_id})")
            self.pending_friend_requests[peer_id] = display_name
            log.info("Showing friend request dialog for %s (%s)", display_name, peer_id)
            
            # Show popup dialog (only once)
            print(f"[DEBUG] Calling _show_friend_request_dialog...")
            self._show_friend_request_dialog(peer_id, display_name)
            print(f"[DEBUG] _show_friend_request_dialog returned")
        except Exception as e:
            import traceback
            # Use the log from module level, don't redefine it
            log.error(f"Error in _on_friend_request_received_signal: {e}")
            traceback.print_exc()
            # Also show error to user
            QMessageBox.critical(self, "Error", f"Error processing friend request: {e}")
    
    def _show_friend_request_dialog(self, peer_id: str, display_name: str):
        """
        Show popup dialog for friend request (runs in main thread).
        Only creates one dialog per peer_id to prevent duplicates.
        """
        print(f"[DEBUG] _show_friend_request_dialog called for {display_name} ({peer_id})")
        # Double-check: Don't create if already exists and visible
        if peer_id in self._active_request_dialogs:
            existing_dialog = self._active_request_dialogs[peer_id]
            if existing_dialog and existing_dialog.isVisible():
                print(f"[DEBUG] Dialog already exists and visible for {peer_id}, skipping")
                log.warning("Dialog already exists and visible for %s, skipping", peer_id)
                return
        
        print(f"[DEBUG] Creating new dialog for {display_name} ({peer_id})")
        # Track active dialog BEFORE creating (prevent race condition)
        dialog = QDialog(self)
        dialog.setWindowTitle("Friend Request")
        dialog.setModal(True)
        dialog.setFixedSize(400, 200)
        
        # Store dialog reference immediately
        self._active_request_dialogs[peer_id] = dialog
        print(f"[DEBUG] Dialog created and stored for {display_name} ({peer_id})")
        log.debug("Created friend request dialog for %s (%s)", display_name, peer_id)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Message
        message_label = QLabel(f"<b>{display_name}</b> wants to be your friend.")
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(message_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        accept_btn = QPushButton("Accept")
        accept_btn.setObjectName("ModernPrimaryButton")
        accept_btn.setFixedHeight(40)
        accept_btn.clicked.connect(lambda: self._on_accept_friend_request(dialog, peer_id))
        
        reject_btn = QPushButton("Reject")
        reject_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ccc;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        reject_btn.setFixedHeight(40)
        reject_btn.clicked.connect(lambda: self._on_reject_friend_request(dialog, peer_id))
        
        button_layout.addWidget(accept_btn)
        button_layout.addWidget(reject_btn)
        layout.addLayout(button_layout)
        
        # Clean up dialog reference when dialog is closed
        def cleanup_dialog():
            if peer_id in self._active_request_dialogs:
                del self._active_request_dialogs[peer_id]
        
        dialog.finished.connect(lambda result: cleanup_dialog())
        
        print(f"[DEBUG] About to call dialog.exec() for {display_name}")
        dialog.exec()
        print(f"[DEBUG] dialog.exec() returned for {display_name}")
    
    def _on_accept_friend_request(self, dialog: QDialog, peer_id: str):
        """Handle Accept button click"""
        # Remove from active dialogs
        if peer_id in self._active_request_dialogs:
            del self._active_request_dialogs[peer_id]
        
        dialog.accept()
        display_name = self.pending_friend_requests.pop(peer_id, "Unknown")
        
        # Accept friend request
        success = self.chat_core.accept_friend(peer_id)
        if success:
            # Refresh UI - peer will be added to known peers by MessageRouter
            self._update_peers_from_core()
            self._refresh_chat_list()
            # Remove peer from suggestions (it's now a friend)
            # MessageRouter will emit temp_peer_removed signal, but we refresh here too
            self._remove_peer_from_suggestions(peer_id)
            
            # Automatically open chat with this peer
            self.current_peer_id = peer_id
            self.unread_counts[peer_id] = 0
            self._load_history_to_center(peer_id)
            self._refresh_chat_list()
            
            QMessageBox.information(self, "Friend Added", f"You are now friends with {display_name}! Chat window opened.")
        else:
            QMessageBox.warning(self, "Error", f"Failed to accept friend request from {display_name}.")
    
    def _on_reject_friend_request(self, dialog: QDialog, peer_id: str):
        """Handle Reject button click"""
        # Remove from active dialogs
        if peer_id in self._active_request_dialogs:
            del self._active_request_dialogs[peer_id]
        
        dialog.reject()
        display_name = self.pending_friend_requests.pop(peer_id, "Unknown")
        
        # Reject friend request
        self.chat_core.reject_friend(peer_id)
        # Remove from incoming_requests tracking (so they can send request again later)
        # No need to refresh UI - peer stays in suggestions
    
    def _on_friend_accepted_signal(self, peer_id: str):
        """
        Handle friend accepted signal (runs in main thread).
        This is connected to chat_core.signals.friend_accepted.
        Called when our friend request is accepted by another peer.
        """
        try:
            # This runs in main thread - safe to update UI
            
            # Remove from pending requests (if was pending)
            self.pending_friend_requests.pop(peer_id, None)
            
            # Refresh UI - peer will be added to known peers by MessageRouter
            self._update_peers_from_core()
            self._refresh_chat_list()
            
            # Remove peer from suggestions (it's now a friend)
            self._remove_peer_from_suggestions(peer_id)
            
            # Find peer name
            peer_name = "Unknown"
            for peer in self.chat_core.get_known_peers():
                if peer["peer_id"] == peer_id:
                    peer_name = peer.get("display_name", "Unknown")
                    break
            
            # Automatically open chat with this peer
            self.current_peer_id = peer_id
            self.unread_counts[peer_id] = 0
            self._load_history_to_center(peer_id)
            self._refresh_chat_list()
            
            QMessageBox.information(self, "Friend Request Accepted", f"{peer_name} accepted your friend request! Chat window opened.")
        except Exception as e:
            import traceback
            # Use the log from module level, don't redefine it
            log.error(f"Error in _on_friend_accepted_signal: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error processing friend accept: {e}")
    
    def _on_friend_rejected_signal(self, peer_id: str):
        """
        Handle friend rejected signal (runs in main thread).
        This is connected to chat_core.signals.friend_rejected.
        Called when our friend request is rejected by another peer.
        """
        try:
            # This runs in main thread - safe to show message
            # Find peer name from temp discovered peers
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

    # ------------------------------------------------------------------ #
    def _cleanup_offline_peers(self):
        """Cleanup offline peers periodically."""
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
