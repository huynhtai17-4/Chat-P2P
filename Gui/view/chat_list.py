from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QListWidget, QListWidgetItem
)
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QAction
import os

from .chat_item import ChatItemWidget 
from Gui.controller.chat_list_controller import ChatListController
from ..utils.avatar import load_circular_pixmap

class ChatList(QFrame):
    def __init__(self, user_name: str = "User", avatar_path: str = None):
        super().__init__()
        self.setObjectName("LeftSidebar")
        self.setMinimumWidth(240) 
        self.setMaximumWidth(450)
        self.setMinimumHeight(500)
        
        self.user_name = user_name
        self.avatar_path = avatar_path

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(5)
        header_layout.setContentsMargins(10, 10, 10, 10)

        user_avatar = QLabel()
        user_avatar.setObjectName("HeaderUserAvatar")
        user_avatar.setFixedSize(60, 60)
        
        if avatar_path and os.path.exists(avatar_path):
            avatar_pixmap = load_circular_pixmap(avatar_path, size=60, border_width=2, border_color="#dddddd")
        else:
            avatar_pixmap = load_circular_pixmap("Gui/assets/images/avatar1.jpg", size=60, border_width=2, border_color="#dddddd")
        user_avatar.setPixmap(avatar_pixmap)
        user_avatar.setAlignment(Qt.AlignCenter)

        user_name_label = QLabel(user_name)
        user_name_label.setObjectName("UserNameLabel")
        user_name_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        header_layout.addWidget(user_avatar)
        header_layout.addWidget(user_name_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setObjectName("HeaderDivider")
        layout.addWidget(divider)

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

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search")
        self.search_input.setObjectName("SearchBar")

        search_action = QAction(QIcon("Gui/assets/icons/search.svg"), "", self.search_input)
        self.search_input.addAction(search_action, QLineEdit.TrailingPosition)

        layout.addWidget(self.search_input)

        self.chat_list_widget = QListWidget()
        self.chat_list_widget.setObjectName("ChatList")
        self.chat_list_widget.setSpacing(5)
        self.chat_list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        layout.addWidget(self.chat_list_widget, 1)
        self.setLayout(layout)

        self.controller = ChatListController(self.chat_list_widget)
        self.controller.set_search_input(self.search_input)
        self.controller.set_tab_labels(self.tab_direct, self.tab_groups, self.tab_public)

    def add_chat(self, name, last_message, time_str, unread_count=0, selected=False, is_online=False, peer_id=None):
        
        chat_item_widget = ChatItemWidget(name, last_message, time_str, unread_count, selected)
        chat_item_widget.set_online_status(is_online)
        if peer_id:
            chat_item_widget.peer_id = peer_id
        list_item = QListWidgetItem(self.chat_list_widget)
        list_item.setSizeHint(chat_item_widget.sizeHint())
        self.chat_list_widget.addItem(list_item)
        self.chat_list_widget.setItemWidget(list_item, chat_item_widget)

    def populate_chat_list(self):
        
        pass
    
    def load_conversations(self, conversations: list):
        
        self.controller.clear_selection()
        self.chat_list_widget.clear()
        self.controller.all_chat_items = []

        for conv in conversations:
            peer_name = conv.get('peer_name', 'Unknown')
            last_message = conv.get('last_message', '')
            time_str = conv.get('time_str', '')
            unread_count = conv.get('unread_count', 0)
            is_online = conv.get('is_online', False)
            peer_id = conv.get('peer_id', '')

            chat_item_widget = ChatItemWidget(
                name=peer_name,
                message=last_message,
                time=time_str,
                unread_count=unread_count,
                is_active=False
            )
            chat_item_widget.set_online_status(is_online)
            chat_item_widget.peer_id = peer_id

            list_item = QListWidgetItem(self.chat_list_widget)
            list_item.setSizeHint(chat_item_widget.sizeHint())
            self.chat_list_widget.addItem(list_item)
            self.chat_list_widget.setItemWidget(list_item, chat_item_widget)

        self.controller._cache_all_chat_items()
    
    def update_peer_status(self, peer_id: str, is_online: bool):
        """Update online status for a specific peer in the chat list"""
        for i in range(self.chat_list_widget.count()):
            item = self.chat_list_widget.item(i)
            if item:
                widget = self.chat_list_widget.itemWidget(item)
                if widget and hasattr(widget, 'peer_id') and widget.peer_id == peer_id:
                    widget.set_online_status(is_online)
                    break

    def get_controller(self):
        return self.controller

    def connect_chat_selected(self, callback):
        
        self.controller.chat_selected.connect(callback)

    def connect_tab_changed(self, callback):
        
        self.controller.tab_changed.connect(callback)

    def connect_search_performed(self, callback):
        
        self.controller.search_performed.connect(callback)
