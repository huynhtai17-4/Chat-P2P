# chat_area.py
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

class ChatArea(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("CenterPanel") # Đổi tên ID để QSS áp dụng
        
        self.setMinimumHeight(300)
        self.setMinimumHeight(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) # Không có viền
        layout.setSpacing(0) # Không có khoảng cách

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
        self.message_layout = QVBoxLayout(message_content) # Layout để thêm tin nhắn
        self.message_layout.setSpacing(10)
        self.message_layout.addStretch() # Đẩy tin nhắn lên trên
        
        message_area.setWidget(message_content)

        # 3. Khung nhập tin nhắn
        input_bar = self._create_input_bar()

        # Thêm 3 phần vào layout
        layout.addWidget(chat_header)
        layout.addWidget(message_area, 1) # 1 = co giãn
        layout.addWidget(input_bar)

        # Thêm tin nhắn mẫu
        self.populate_messages()

    def _create_chat_header(self):
        """Hàm private tạo header cho khung chat"""
        header_frame = QFrame()
        header_frame.setObjectName("ChatHeader")
        
        layout = QHBoxLayout(header_frame)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 5, 10, 5)  # Bạn có thể chỉnh viền theo ý

        # Avatar
        avatar = QLabel()
        avatar.setObjectName("AvatarLabel")
        avatar.setFixedSize(40, 40)  # Kích thước avatar
        avatar.setPixmap(load_circular_pixmap("Gui/assets/images/avatar.jpg", size= 40))
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

        phone_icon = QPushButton()
        phone_icon.setIcon(QIcon("Gui/assets/icons/phone.svg"))
        phone_icon.setIconSize(QSize(22, 22))
        phone_icon.setFlat(True)
        phone_icon.setObjectName("IconButton")

        video_icon = QPushButton()
        video_icon.setIcon(QIcon("Gui/assets/icons/video.svg"))
        video_icon.setIconSize(QSize(22, 22))
        video_icon.setFlat(True)
        video_icon.setObjectName("IconButton")

        more_icon = QPushButton()
        more_icon.setIcon(QIcon("Gui/assets/icons/more-horizontal.svg"))
        more_icon.setIconSize(QSize(22, 22))
        more_icon.setFlat(True)
        more_icon.setObjectName("IconButton")

        icons_layout.addWidget(phone_icon)
        icons_layout.addWidget(video_icon)
        icons_layout.addWidget(more_icon)

        # Thêm các phần vào layout chính
        layout.addWidget(avatar)
        layout.addLayout(text_layout)
        layout.addStretch()          # Đẩy icons sang phải
        layout.addLayout(icons_layout)

        return header_frame


    def _create_input_bar(self):
        """Hàm private tạo khung nhập tin nhắn ở dưới cùng"""
        input_frame = QFrame()
        input_frame.setObjectName("ChatInputBar")
        
        layout = QHBoxLayout(input_frame)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        clip_icon = QPushButton()
        clip_icon.setIcon(QIcon("Gui/assets/icons/link.svg"))
        clip_icon.setIconSize(QSize(22, 22))
        clip_icon.setFlat(True)
        clip_icon.setObjectName("IconButton")

        emoji_icon = QPushButton()
        emoji_icon.setIcon(QIcon("Gui/assets/icons/smile.svg"))
        emoji_icon.setIconSize(QSize(22, 22))
        emoji_icon.setFlat(True)
        emoji_icon.setObjectName("IconButton")
        
        mic_icon = QPushButton()
        mic_icon.setIcon(QIcon("Gui/assets/icons/mic.svg"))
        mic_icon.setIconSize(QSize(22, 22))
        mic_icon.setFlat(True)
        mic_icon.setObjectName("IconButton")

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message here...")
        self.message_input.setObjectName("MessageInput")
        
        send_button = QPushButton()
        send_button.setIcon(QIcon("Gui/assets/icons/send.svg"))
        send_button.setIconSize(QSize(22, 22))
        send_button.setFlat(True)
        send_button.setObjectName("IconButton")
        
        layout.addWidget(clip_icon)
        layout.addWidget(emoji_icon)
        layout.addWidget(mic_icon)
        layout.addWidget(self.message_input, 1) # 1 = co giãn
        layout.addWidget(send_button)

        return input_frame

    def add_message(self, text, is_sender, add_to_top=False):
        
        bubble = MessageBubble(text, is_sender)
        
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10) # Khoảng cách giữa avatar và bubble
        
        if is_sender:
            # Tin nhắn của mình: [Stretch] [Bubble]
            row_layout.addStretch() 
            row_layout.addWidget(bubble, 0, Qt.AlignTop | Qt.AlignRight)
        else:
            
            # 1. Tạo Avatar
            avatar_label = QLabel()
            avatar_label.setObjectName("ChatAvatarLabel") # ID riêng cho avatar trong chat
            avatar_label.setFixedSize(36, 36) # Kích thước nhỏ hơn avatar header
            
            # (Bạn có thể đổi "avatar.jpg" thành avatar của người gửi)
            avatar_pixmap = load_circular_pixmap("Gui/assets/images/avatar.jpg", size=36)
            avatar_label.setPixmap(avatar_pixmap)

            # 2. Thêm vào layout
            row_layout.addWidget(avatar_label)
            row_layout.addWidget(bubble)
            row_layout.addStretch()
            
            # 3. Căn cả hàng lên trên
            # (Quan trọng: để avatar căn đúng với dòng đầu tiên của bubble)
            row_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft) 
        
        # (self.message_layout.count() - 1) để luôn chèn TRÊN stretch
        self.message_layout.insertLayout(self.message_layout.count() - 1, row_layout)
        
    def add_date_separator(self, text):
        """Thêm dấu phân cách ngày tháng"""
        label = QLabel(text)
        label.setObjectName("DateSeparator")
        self.message_layout.insertWidget(self.message_layout.count() - 1, label)

    def populate_messages(self):
        """Thêm dữ liệu mẫu"""
        self.add_date_separator("Today 12:21 AM")
        self.add_message("Let's together work on this an create something more awesome.", False)
        self.add_message("Hey! Listen", True)
        self.add_message("I really like your idea, but I still think we can do more in this.", True)
        self.add_message("I will share something", True)
        self.add_message("Sounds perfect", True)