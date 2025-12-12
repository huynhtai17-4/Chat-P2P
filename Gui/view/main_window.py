from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QSplitter, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt

from .chat_list import ChatList
from .chat_area import ChatArea
from .notifications_panel import NotificationsPanel
from ..controller.main_window_controller import MainWindowController


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
        self._active_request_dialogs = {}

        self.controller = MainWindowController(self.username, self.user_name, self.tcp_port)
        self.controller.setParent(self)
        self._setup_ui()
        self._setup_controller_signals()
        self._setup_component_signals()
        self.controller.start()
        
        local_ip = getattr(self.controller.chat_core, 'local_ip', '')
        self.right_sidebar.set_user_network_info(local_ip, self.tcp_port)

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

    def _setup_controller_signals(self):
        self.controller.chat_list_updated.connect(self._on_chat_list_updated)
        self.controller.message_received.connect(self._on_message_received)
        self.controller.chat_selected.connect(self._on_chat_selected)
        self.controller.show_friend_request_dialog.connect(self._show_friend_request_dialog)
        self.controller.show_message_box.connect(self._show_message_box)
        self.controller.load_chat_history.connect(self._on_load_chat_history)

    def _setup_component_signals(self):
        chat_list_controller = self.left_sidebar.get_controller()
        chat_list_controller.set_peer_refresh_handler(self.controller._update_peers_from_core)
        self.left_sidebar.connect_chat_selected(self.controller.on_chat_selected)

        chat_area_controller = self.center_panel.get_controller()
        chat_area_controller.set_send_handler(self.controller.send_message)
        
        def handle_file(file_path, file_name, file_data_base64, is_image):
            self.controller.handle_file_attached(file_path, file_name, file_data_base64, is_image)
        
        self.center_panel.connect_file_attached(handle_file)
        
        self.controller.add_preview_callback = lambda name, data, is_img: self.center_panel.add_preview_item(name, data, is_img)
        self.controller.clear_preview_callback = lambda: self.center_panel.clear_preview()
        
        self.center_panel.remove_friend_requested.connect(self.controller.remove_friend)
        
        self.center_panel.voice_call_requested.connect(self.controller.start_voice_call)
        self.center_panel.video_call_requested.connect(self.controller.start_video_call)

        self.right_sidebar.add_friend_requested.connect(self._on_add_friend_requested)
        
        self.controller._update_peer_status_callback = self._update_peer_status_in_list
        self.controller._update_header_status_callback = self._update_header_status

    def _on_chat_list_updated(self, conversations):
        self.left_sidebar.load_conversations(conversations)
        if self.controller.current_peer_id:
            peers = self.controller.peers
            peer_info = peers.get(self.controller.current_peer_id, {})
            if peer_info:
                peer_name = peer_info.get('display_name', 'Unknown')
                is_online = peer_info.get('status', '') == 'online'
                avatar_path = peer_info.get('avatar_path')
                self.center_panel.set_peer_info(
                    peer_name=peer_name,
                    peer_id=self.controller.current_peer_id,
                    is_online=is_online,
                    avatar_path=avatar_path
                )
        else:
            self.center_panel.hide_header()
    
    def _update_peer_status_in_list(self, peer_id: str, is_online: bool):
        if self.left_sidebar:
            self.left_sidebar.update_peer_status(peer_id, is_online)

    def _on_message_received(self, payload):
        peer_id = payload.get("peer_id", "")
        is_sender = payload.get("is_sender", False)
        display_content = payload.get("display_content", payload.get("content", ""))
        time_str = payload.get("time_str", "")
        file_name = payload.get("file_name")
        file_data = payload.get("file_data")
        local_file_path = payload.get("local_file_path")
        msg_type = payload.get("msg_type", "text")
        
        if peer_id == self.controller.current_peer_id and self.center_panel:
            self.center_panel.add_message(
                display_content, 
                is_sender,
                time_str=time_str,
                file_name=file_name,
                file_data=file_data,
                msg_type=msg_type,
                local_file_path=local_file_path,
            )

    def _on_chat_selected(self, chat_id: str, chat_name: str):
        if chat_id and chat_name:
            peers = self.controller.peers
            peer_info = peers.get(chat_id, {})
            is_online = peer_info.get('status', '') == 'online'
            avatar_path = peer_info.get('avatar_path')
            
            self.center_panel.set_peer_info(
                peer_name=chat_name,
                peer_id=chat_id,
                is_online=is_online,
                avatar_path=avatar_path
            )
        else:
            self.center_panel.hide_header()
    
    def _update_header_status(self, peer_id: str, is_online: bool):
        if peer_id == self.controller.current_peer_id:
            self.center_panel.set_peer_status(is_online)

    def _on_load_chat_history(self, peer_id: str, history: list):
        if self.center_panel:
            if peer_id:
                peers = self.controller.peers
                peer_info = peers.get(peer_id, {})
                peer_name = peer_info.get('display_name', 'Unknown')
                is_online = peer_info.get('status', '') == 'online'
                avatar_path = peer_info.get('avatar_path')
                self.center_panel.set_peer_info(
                    peer_name=peer_name,
                    peer_id=peer_id,
                    is_online=is_online,
                    avatar_path=avatar_path
                )
            self.center_panel.load_chat_history(history)

    def _show_friend_request_dialog(self, peer_id: str, display_name: str):
        if peer_id in self._active_request_dialogs:
            existing_dialog = self._active_request_dialogs[peer_id]
            if existing_dialog and existing_dialog.isVisible():
                return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Friend Request")
        dialog.setModal(True)
        dialog.setFixedSize(400, 200)
        
        self._active_request_dialogs[peer_id] = dialog
        
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
        reject_btn.setStyleSheet("")
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
        self.controller.on_accept_friend_request(peer_id)

    def _on_reject_friend_request(self, dialog: QDialog, peer_id: str):
        if peer_id in self._active_request_dialogs:
            del self._active_request_dialogs[peer_id]
        dialog.reject()
        self.controller.on_reject_friend_request(peer_id)

    def _show_message_box(self, msg_type: str, title: str, message: str):
        if msg_type == "error":
            QMessageBox.critical(self, title, message)
        elif msg_type == "warning":
            QMessageBox.warning(self, title, message)
        elif msg_type == "info":
            QMessageBox.information(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    def _on_add_friend_requested(self, ip: str, port: int):
        if self.controller:
            self.controller.add_friend_by_ip(ip, port)
    
    def closeEvent(self, event):
        self.controller.stop()
        event.accept()
