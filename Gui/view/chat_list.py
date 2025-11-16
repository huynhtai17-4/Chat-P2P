# chat_list.py (cập nhật)
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QListWidget, QListWidgetItem
)
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QLineEdit
from ..utils.avatar import load_circular_pixmap

# Import component con
from .chat_item import ChatItemWidget 
from Gui.controller.chat_list_controller import ChatListController

class ChatList(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("LeftSidebar")
        self.setMinimumWidth(240) 
        self.setMaximumWidth(450)
        self.setMinimumHeight(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Header: Avatar + Tên người dùng
        header_layout = QHBoxLayout()
        header_layout.setSpacing(5)
        header_layout.setContentsMargins(10, 10, 10, 10)

        user_avatar = QLabel()
        user_avatar.setObjectName("HeaderUserAvatar")
        user_avatar.setFixedSize(60, 60)
        avatar_pixmap = load_circular_pixmap("Gui/assets/images/avatar1.jpg", size=60, border_width=2, border_color="#dddddd")
        user_avatar.setPixmap(avatar_pixmap)
        user_avatar.setAlignment(Qt.AlignCenter)

        user_name = QLabel("Tài Huỳnh")
        user_name.setObjectName("UserNameLabel")
        user_name.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        header_layout.addWidget(user_avatar)
        header_layout.addWidget(user_name)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Đường kẻ ngang
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setObjectName("HeaderDivider")
        layout.addWidget(divider)

        # Tiêu đề "Chats" và nút +
        title_layout = QHBoxLayout()
        title_label = QLabel("Chats")
        title_label.setObjectName("ChatsHeader") 
        
        plus_btn = QPushButton()
        plus_btn.setIcon(QIcon("Gui/assets/icons/plus.svg"))
        plus_btn.setIconSize(QSize(22, 22))
        plus_btn.setFlat(True)
        plus_btn.setObjectName("PlusButton")
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(plus_btn)
        
        layout.addLayout(title_layout)

        # Các Tab (DIRECT, GROUPS, PUBLIC)
        tab_layout = QHBoxLayout()
        
        self.tab_direct = QLabel("DIRECT")
        self.tab_direct.setProperty("class", "TabLabel") 
        
        self.tab_groups = QLabel("GROUPS")
        self.tab_groups.setProperty("class", "TabLabel") 
        
        self.tab_public = QLabel("PUBLIC")
        self.tab_public.setProperty("class", "TabLabel")

        tab_layout.addStretch(1)
        tab_layout.addWidget(self.tab_direct)
        tab_layout.addStretch(1)
        tab_layout.addWidget(self.tab_groups)
        tab_layout.addStretch(1)
        tab_layout.addWidget(self.tab_public)
        tab_layout.addStretch(1)
        
        layout.addLayout(tab_layout)

        # Thanh tìm kiếm
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search")
        self.search_input.setObjectName("SearchBar")

        search_action = QAction(QIcon("Gui/assets/icons/search.svg"), "", self.search_input)
        self.search_input.addAction(search_action, QLineEdit.TrailingPosition)

        layout.addWidget(self.search_input)

        # Danh sách Chat
        self.chat_list_widget = QListWidget()
        self.chat_list_widget.setObjectName("ChatList")
        self.chat_list_widget.setSpacing(5)
        self.chat_list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        layout.addWidget(self.chat_list_widget, 1)
        self.setLayout(layout)

        # Khởi tạo controller
        self.controller = ChatListController(self.chat_list_widget)
        self.controller.set_search_input(self.search_input)
        self.controller.set_tab_labels(self.tab_direct, self.tab_groups, self.tab_public)

        # Thêm dữ liệu mẫu
        self.populate_chat_list()

    def add_chat(self, name, last_message, time_str, unread_count=0, selected=False):
        """Hàm trợ giúp để thêm ChatItemWidget vào QListWidget"""
        chat_item_widget = ChatItemWidget(name, last_message, time_str, unread_count, selected)
        list_item = QListWidgetItem(self.chat_list_widget)
        list_item.setSizeHint(chat_item_widget.sizeHint())
        self.chat_list_widget.addItem(list_item)
        self.chat_list_widget.setItemWidget(list_item, chat_item_widget)

    def populate_chat_list(self):
        """Thêm dữ liệu mẫu"""
        chats_data = [
            ("Ankit Mishra", "Are we meeting today? Get's aaaaaaaaaaaaaaaaaaaaaaaaaaaaa ", "3:43 PM", 5, False),
            ("Akenksha Sinha", "I've mailed you the file check...", "2:34 PM", 0, False),
            ("Harshit Nagar", "last night party was awesome...", "3:01 PM", 0, False),
            ("Kirti Yadav", "Are you there ?", "9:00 AM", 0, False),
            ("Ashish Singh", "Bro, I need your help. Call me...", "9:15 AM", 0, False),
            ("Harshit Nagar", "last night party was awesome...", "1:42 PM", 0, False),
            ("Kirti yadav", "Are you there ?", "9:00 AM", 0, False),
            ("Ashish Singh", "Bro, I need your help. Call me...", "9:00 AM", 0, False),
        ]
        for name, msg, time_str, unread, selected in chats_data:
            self.add_chat(name, msg, time_str, unread, selected)

    # Các method để tương tác với controller từ bên ngoài
    def get_controller(self):
        return self.controller

    def connect_chat_selected(self, callback):
        """Kết nối signal chat selected với callback"""
        self.controller.chat_selected.connect(callback)

    def connect_tab_changed(self, callback):
        """Kết nối signal tab changed với callback"""
        self.controller.tab_changed.connect(callback)

    def connect_search_performed(self, callback):
        """Kết nối signal search performed với callback"""
        self.controller.search_performed.connect(callback)