# chat_area.py (cập nhật)
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize
from ..utils.avatar import load_circular_pixmap

# Import component con
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

        # 1. Header (Thông tin Kirti Yadav)
        chat_header = self._create_chat_header()
        
        # 2. Khu vực tin nhắn (Phải dùng QScrollArea)
        message_area = QScrollArea()
        message_area.setObjectName("MessageArea")
        message_area.setWidgetResizable(True)
        message_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Widget chứa nội dung bên trong ScrollArea
        message_content = QWidget()
        message_content.setObjectName("MessageContent")
        self.message_layout = QVBoxLayout(message_content)
        self.message_layout.setSpacing(10)
        self.message_layout.addStretch()
        
        message_area.setWidget(message_content)

        # 3. Khung nhập tin nhắn
        input_bar = self._create_input_bar()

        # Thêm 3 phần vào layout
        layout.addWidget(chat_header)
        layout.addWidget(message_area, 1)
        layout.addWidget(input_bar)

        # Khởi tạo controller
        self.controller = ChatAreaController(self)
        self._setup_controller()

        # Thêm tin nhắn mẫu
        self.populate_messages()

    def _create_chat_header(self):
        """Hàm private tạo header cho khung chat"""
        header_frame = QFrame()
        header_frame.setObjectName("ChatHeader")
        
        layout = QHBoxLayout(header_frame)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 5, 10, 5)

        # Avatar
        avatar = QLabel()
        avatar.setObjectName("AvatarLabel")
        avatar.setFixedSize(40, 40)
        avatar.setPixmap(load_circular_pixmap("Gui/assets/images/avatar.jpg", size=40))
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setScaledContents(True)

        # Thông tin tên và trạng thái
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        name = QLabel("Kirti Yadav")
        name.setObjectName("NameLabel")
        status = QLabel("Last seen 3 hours ago")
        status.setObjectName("MessageLabel")
        text_layout.addWidget(name)
        text_layout.addWidget(status)

        # Icons bên phải
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

        # Thêm các phần vào layout chính
        layout.addWidget(avatar)
        layout.addLayout(text_layout)
        layout.addStretch()
        layout.addLayout(icons_layout)

        return header_frame

    def _create_input_bar(self):
        """Hàm private tạo khung nhập tin nhắn ở dưới cùng"""
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
        
        self.mic_icon = QPushButton()
        self.mic_icon.setIcon(QIcon("Gui/assets/icons/mic.svg"))
        self.mic_icon.setIconSize(QSize(22, 22))
        self.mic_icon.setFlat(True)
        self.mic_icon.setObjectName("IconButton")

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
        layout.addWidget(self.mic_icon)
        layout.addWidget(self.message_input, 1)
        layout.addWidget(self.send_button)

        return input_frame

    def _setup_controller(self):
        """Thiết lập controller với các widget"""
        self.controller.set_message_input(self.message_input)
        self.controller.set_attach_button(self.clip_icon)
        self.controller.set_emoji_button(self.emoji_icon)
        self.controller.set_send_button(self.send_button)

    def add_message(self, text, is_sender, add_to_top=False, time_str=None):
        """
        Add a message bubble to the chat area.
        
        Args:
            text: Message content
            is_sender: True if message is from current user, False otherwise
            add_to_top: If True, add message at the top (for history loading)
            time_str: Optional timestamp string (e.g., "14:30")
        """
        bubble = MessageBubble(text, is_sender, time_str=time_str)
        # Get the widget to add (container if timestamp exists, bubble itself otherwise)
        bubble_widget = bubble.get_widget()
        
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        
        if is_sender:
            row_layout.addStretch() 
            row_layout.addWidget(bubble_widget, 0, Qt.AlignTop | Qt.AlignRight)
        else:
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
        
        # Auto-scroll to bottom when new message is added (realtime)
        # Find the parent QScrollArea
        from PySide6.QtCore import QTimer
        parent = self.parent()
        while parent:
            if isinstance(parent, QScrollArea):
                # Use QTimer.singleShot to ensure layout is updated before scrolling
                QTimer.singleShot(10, lambda sa=parent: sa.verticalScrollBar().setValue(
                    sa.verticalScrollBar().maximum()
                ))
                break
            parent = parent.parent()
        
    def add_date_separator(self, text):
        """Thêm dấu phân cách ngày tháng"""
        label = QLabel(text)
        label.setObjectName("DateSeparator")
        self.message_layout.insertWidget(self.message_layout.count() - 1, label)

    def populate_messages(self):
        """Thêm dữ liệu mẫu (deprecated - use load_chat_history)"""
        # This method is kept for compatibility but not used
        # Use load_chat_history() instead to load actual chat history
        pass
    
    def load_chat_history(self, messages: list):
        """Load chat history from list of message dicts"""
        # Clear existing messages (except stretch)
        self.clear_messages()
        
        if not messages:
            return
        
        # Group messages by date
        current_date = None
        
        for msg in messages:
            msg_date = msg.get('date_str')
            
            # Add date separator if date changed
            if msg_date != current_date:
                self.add_date_separator(msg_date)
                current_date = msg_date
            
            # Add message
            is_sender = msg.get('is_sender', False)
            content = msg.get('content', '')
            time_str = msg.get('time_str', None)
            self.add_message(content, is_sender, time_str=time_str)
    
    def clear_messages(self):
        """Clear all messages from chat area"""
        # Remove all items except the stretch at the end
        while self.message_layout.count() > 1:
            item = self.message_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
    
    def _clear_layout(self, layout):
        """Recursively clear a layout"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    # Các method để tương tác với controller từ bên ngoài
    def get_controller(self):
        return self.controller

    def connect_file_attached(self, callback):
        """Kết nối signal file attached với callback"""
        self.controller.file_attached.connect(callback)

    def connect_emoji_selected(self, callback):
        """Kết nối signal emoji selected với callback"""
        self.controller.emoji_selected.connect(callback)

    def connect_message_sent(self, callback):
        """Kết nối signal message sent với callback"""
        self.controller.message_sent.connect(callback)