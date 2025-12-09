from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QSize
import os
import base64
from ..utils.avatar import load_circular_pixmap

from .message_bubble import MessageBubble
from Gui.controller.chat_area_controller import ChatAreaController

class ChatArea(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("CenterPanel")
        self.setMinimumHeight(300)
        self.setMinimumHeight(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        chat_header = self._create_chat_header()
        
        self.message_area = QScrollArea()
        self.message_area.setObjectName("MessageArea")
        self.message_area.setWidgetResizable(True)
        self.message_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.message_content = QWidget()
        self.message_content.setObjectName("MessageContent")
        self.message_layout = QVBoxLayout(self.message_content)
        self.message_layout.setSpacing(10)
        self.message_layout.addStretch()
        
        self.message_area.setWidget(self.message_content)
        # Auto-scroll whenever the scroll range changes (new content added)
        self.message_area.verticalScrollBar().rangeChanged.connect(
            lambda _min, _max: self.scroll_to_bottom()
        )

        input_bar = self._create_input_bar()

        layout.addWidget(chat_header)
        layout.addWidget(self.message_area, 1)
        layout.addWidget(input_bar)

        self.controller = ChatAreaController(self)
        self._setup_controller()

        self.populate_messages()
    
    def set_peer_info(self, peer_name: str, peer_id: str = "", is_online: bool = False, avatar_path: str = None):
        """Update chat header with peer info and show header"""
        self.header_name.setText(peer_name)
        
        if is_online:
            self.header_status.setText("Online")
        else:
            self.header_status.setText("Offline")
        
        # Load avatar
        if avatar_path and os.path.exists(avatar_path):
            pixmap = load_circular_pixmap(avatar_path, size=40)
        else:
            # Use default avatar
            pixmap = load_circular_pixmap("Gui/assets/images/avatar1.jpg", size=40)
        self.header_avatar.setPixmap(pixmap)
        
        # Show header
        self.header_frame.setVisible(True)
    
    def hide_header(self):
        """Hide chat header when no peer selected"""
        self.header_frame.setVisible(False)
    
    def set_peer_status(self, is_online: bool):
        """Update only the status text in the header"""
        if is_online:
            self.header_status.setText("Online")
        else:
            self.header_status.setText("Offline")

    def _create_chat_header(self):
        
        self.header_frame = QFrame()
        self.header_frame.setObjectName("ChatHeader")
        self.header_frame.setVisible(False)  # Hidden by default until peer selected
        
        layout = QHBoxLayout(self.header_frame)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 5, 10, 5)

        self.header_avatar = QLabel()
        self.header_avatar.setObjectName("AvatarLabel")
        self.header_avatar.setFixedSize(40, 40)
        self.header_avatar.setPixmap(load_circular_pixmap("Gui/assets/images/avatar1.jpg", size=40))
        self.header_avatar.setAlignment(Qt.AlignCenter)
        self.header_avatar.setScaledContents(True)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        self.header_name = QLabel("No chat selected")
        self.header_name.setObjectName("NameLabel")
        self.header_status = QLabel("")
        self.header_status.setObjectName("MessageLabel")
        text_layout.addWidget(self.header_name)
        text_layout.addWidget(self.header_status)

        icons_layout = QHBoxLayout()
        icons_layout.setSpacing(15)

        self.phone_icon = QPushButton()
        self.phone_icon.setIcon(QIcon("Gui/assets/icons/phone.svg"))
        self.phone_icon.setIconSize(QSize(22, 22))
        self.phone_icon.setFlat(True)
        self.phone_icon.setObjectName("IconButton")

        self.video_icon = QPushButton()
        self.video_icon.setIcon(QIcon("Gui/assets/icons/video.svg"))
        self.video_icon.setIconSize(QSize(22, 22))
        self.video_icon.setFlat(True)
        self.video_icon.setObjectName("IconButton")

        self.more_icon = QPushButton()
        self.more_icon.setIcon(QIcon("Gui/assets/icons/more-horizontal.svg"))
        self.more_icon.setIconSize(QSize(22, 22))
        self.more_icon.setFlat(True)
        self.more_icon.setObjectName("IconButton")

        icons_layout.addWidget(self.phone_icon)
        icons_layout.addWidget(self.video_icon)
        icons_layout.addWidget(self.more_icon)

        layout.addWidget(self.header_avatar)
        layout.addLayout(text_layout)
        layout.addStretch()
        layout.addLayout(icons_layout)

        return self.header_frame

    def _create_input_bar(self):
        
        input_container = QWidget()
        input_container.setObjectName("ChatInputContainer")
        
        main_layout = QVBoxLayout(input_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.preview_area = QWidget()
        self.preview_area.setObjectName("PreviewArea")
        self.preview_area.setVisible(False)
        preview_layout = QVBoxLayout(self.preview_area)
        preview_layout.setContentsMargins(10, 8, 10, 8)
        preview_layout.setSpacing(8)
        
        self.preview_items_layout = QVBoxLayout()
        self.preview_items_layout.setSpacing(8)
        preview_layout.addLayout(self.preview_items_layout)
        
        main_layout.addWidget(self.preview_area)
        
        input_frame = QFrame()
        input_frame.setObjectName("ChatInputBar")
        
        layout = QHBoxLayout(input_frame)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        self.clip_icon = QPushButton()
        self.clip_icon.setIcon(QIcon("Gui/assets/icons/link.svg"))
        self.clip_icon.setIconSize(QSize(22, 22))
        self.clip_icon.setFlat(True)
        self.clip_icon.setObjectName("IconButton")

        self.emoji_icon = QPushButton()
        self.emoji_icon.setIcon(QIcon("Gui/assets/icons/smile.svg"))
        self.emoji_icon.setIconSize(QSize(22, 22))
        self.emoji_icon.setFlat(True)
        self.emoji_icon.setObjectName("IconButton")

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message here...")
        self.message_input.setObjectName("MessageInput")
        
        self.send_button = QPushButton()
        self.send_button.setIcon(QIcon("Gui/assets/icons/send.svg"))
        self.send_button.setIconSize(QSize(22, 22))
        self.send_button.setFlat(True)
        self.send_button.setObjectName("IconButton")
        
        layout.addWidget(self.clip_icon)
        layout.addWidget(self.emoji_icon)
        layout.addWidget(self.message_input, 1)
        layout.addWidget(self.send_button)
        
        main_layout.addWidget(input_frame)
        
        self.preview_items = {}
        
        return input_container

    def _setup_controller(self):
        
        self.controller.set_message_input(self.message_input)
        self.controller.set_attach_button(self.clip_icon)
        self.controller.set_emoji_button(self.emoji_icon)
        self.controller.set_send_button(self.send_button)

    def add_message(self, text, is_sender, add_to_top=False, time_str=None, file_name=None, file_data=None, msg_type="text", local_file_path=None):
        """
        Add a message to the chat area.
        
        Args:
            text: Message content
            is_sender: True if message was sent by local user (right aligned), False if received (left aligned)
            time_str: Timestamp string
            file_name: File name if message contains a file
            file_data: Base64 encoded file data
            msg_type: Message type ("text", "image", "file", etc.)
            local_file_path: Local path to saved file
        """
        # Ensure is_sender is a boolean
        is_sender = bool(is_sender)
        
        bubble = MessageBubble(
            text,
            is_sender,
            time_str=time_str,
            file_name=file_name,
            file_data=file_data,
            msg_type=msg_type,
            local_file_path=local_file_path,
        )
        bubble_widget = bubble.get_widget()
        bubble_widget.setMaximumWidth(420)
        
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        
        if is_sender:
            # Own message: align to right, no avatar
            row_layout.addStretch() 
            row_layout.addWidget(bubble_widget, 0, Qt.AlignTop | Qt.AlignRight)
        else:
            # Incoming message: align to left, show avatar
            avatar_label = QLabel()
            avatar_label.setObjectName("ChatAvatarLabel")
            avatar_label.setFixedSize(36, 36)
            avatar_pixmap = load_circular_pixmap("Gui/assets/images/avatar.jpg", size=36)
            avatar_label.setPixmap(avatar_pixmap)

            row_layout.addWidget(avatar_label)
            row_layout.addWidget(bubble_widget)
            row_layout.addStretch()
            row_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.message_layout.insertLayout(self.message_layout.count() - 1, row_layout)
        
        # Auto-scroll logic: always scroll to bottom after adding a new message
        self.scroll_to_bottom()
        
    def add_date_separator(self, text):
        
        label = QLabel(text)
        label.setObjectName("DateSeparator")
        self.message_layout.insertWidget(self.message_layout.count() - 1, label)

    def populate_messages(self):
        
        pass
    
    def load_chat_history(self, messages: list):
        
        self.clear_messages()
        
        if not messages:
            return
        
        current_date = None
        
        for msg in messages:
            msg_date = msg.get('date_str')
            
            if msg_date != current_date:
                self.add_date_separator(msg_date)
                current_date = msg_date
            
            # Explicitly get is_sender - determines if message is from local user
            is_sender = bool(msg.get('is_sender', False))
            content = msg.get('content', '')
            time_str = msg.get('time_str', None)
            file_name = msg.get('file_name')
            file_data = msg.get('file_data')
            msg_type = msg.get('msg_type', 'text')
            local_file_path = msg.get('local_file_path')
            self.add_message(
                content,
                is_sender,  # True = own message (right), False = incoming (left)
                time_str=time_str,
                file_name=file_name,
                file_data=file_data,
                msg_type=msg_type,
                local_file_path=local_file_path,
            )
        
        # After loading history, ensure we are at the bottom to show newest
        self.scroll_to_bottom()
    
    def clear_messages(self):
        
        while self.message_layout.count() > 1:
            item = self.message_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
    
    def _clear_layout(self, layout):
        
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def get_controller(self):
        return self.controller

    def connect_file_attached(self, callback):
        self.controller.file_attached.connect(callback)

    def connect_emoji_selected(self, callback):
        
        self.controller.emoji_selected.connect(callback)

    def connect_message_sent(self, callback):
        
        self.controller.message_sent.connect(callback)
    
    def add_preview_item(self, file_name: str, file_data_base64: str, is_image: bool):
        preview_item = QWidget()
        preview_item.setObjectName("PreviewItem")
        preview_item.setStyleSheet("""
            QWidget#PreviewItem {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        item_layout = QHBoxLayout(preview_item)
        item_layout.setContentsMargins(8, 8, 8, 8)
        item_layout.setSpacing(10)
        
        if is_image:
            try:
                image_data = base64.b64decode(file_data_base64)
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                
                max_size = 60
                if pixmap.width() > max_size or pixmap.height() > max_size:
                    pixmap = pixmap.scaled(max_size, max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                image_label = QLabel()
                image_label.setPixmap(pixmap)
                image_label.setFixedSize(max_size, max_size)
                image_label.setStyleSheet("border-radius: 4px;")
                item_layout.addWidget(image_label)
            except:
                icon_label = QLabel("🖼️")
                icon_label.setStyleSheet("font-size: 24px;")
                item_layout.addWidget(icon_label)
        else:
            icon_label = QLabel("📄")
            icon_label.setStyleSheet("font-size: 24px;")
            item_layout.addWidget(icon_label)
        
        name_label = QLabel(file_name)
        name_label.setStyleSheet("font-size: 12px; color: #333;")
        name_label.setWordWrap(True)
        item_layout.addWidget(name_label, 1)
        
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
        """)
        remove_btn.clicked.connect(lambda: self.remove_preview_item(file_name))
        item_layout.addWidget(remove_btn)
        
        self.preview_items[file_name] = (preview_item, file_data_base64, is_image)
        self.preview_items_layout.addWidget(preview_item)
        self.preview_area.setVisible(True)
    
    def remove_preview_item(self, file_name: str):
        if file_name in self.preview_items:
            item_widget, _, _ = self.preview_items[file_name]
            self.preview_items_layout.removeWidget(item_widget)
            item_widget.deleteLater()
            del self.preview_items[file_name]
            
            if len(self.preview_items) == 0:
                self.preview_area.setVisible(False)
    
    def clear_preview(self):
        for file_name in list(self.preview_items.keys()):
            self.remove_preview_item(file_name)
    
    def get_preview_items(self):
        return self.preview_items

    def scroll_to_bottom(self):
        """Force the scroll area to the bottom."""
        if not hasattr(self, "message_area"):
            return
        from PySide6.QtCore import QTimer
        scroll_bar = self.message_area.verticalScrollBar()
        QTimer.singleShot(0, lambda: scroll_bar.setValue(scroll_bar.maximum()))
