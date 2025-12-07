from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
from PySide6.QtCore import Qt, Signal

class NotificationItem(QFrame):
    def __init__(self, username, text, time_ago):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(10)
        avatar = QLabel()
        avatar.setObjectName("NotificationAvatar")
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        txt = f"<b>@{username}</b> {text}"
        label = QLabel(txt)
        label.setWordWrap(False)
        label.setTextFormat(Qt.RichText) 
        
        label.setStyleSheet("font-size: 13px; color: #555;")
        time_label = QLabel(time_ago)
        time_label.setStyleSheet("color: #AAA; font-size: 11px;")
        text_layout.addWidget(label)
        text_layout.addWidget(time_label)
        layout.addWidget(avatar)
        layout.addLayout(text_layout, 1)

class SuggestionItem(QFrame):
    add_requested = Signal(str, str)  # peer_id, peer_name
    chat_requested = Signal(str, str)  # peer_id, peer_name
    
    def __init__(self, name, status_text="Online", peer_id=None, is_added=False):
        super().__init__()
        self.peer_id = peer_id
        self.peer_name = name
        self.is_added = is_added
        
        self.setObjectName("SuggestionItem")
        self.setVisible(True)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(10)
        
        avatar_container = QFrame()
        avatar_container.setObjectName("AvatarContainer")
        avatar_layout = QVBoxLayout(avatar_container)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.setSpacing(0)
        
        avatar = QLabel()
        avatar.setObjectName("NotificationAvatar")
        avatar_layout.addWidget(avatar)
        
        self.online_indicator = QLabel()
        self.online_indicator.setObjectName("OnlineIndicator")
        self.online_indicator.setFixedSize(12, 12)
        is_online = status_text.lower() == "online"
        self.online_indicator.setVisible(is_online)
        avatar_layout.addWidget(self.online_indicator, 0, Qt.AlignRight | Qt.AlignBottom)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        txt = f"<b>@{name}</b>"
        label = QLabel(txt)
        label.setWordWrap(False)
        label.setTextFormat(Qt.RichText)
        label.setStyleSheet("font-size: 13px; color: #555;")
        
        status_label = QLabel(status_text)
        if is_online:
            status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")  # Green for online
        else:
            status_label.setStyleSheet("color: #999; font-size: 11px;")  # Gray for offline
        
        text_layout.addWidget(label)
        text_layout.addWidget(status_label)
        
        layout.addWidget(avatar_container)
        layout.addLayout(text_layout, 1)
        
        if not is_added:
            self.add_button = QPushButton("Add")
            self.add_button.setObjectName("AddButton")
            self.add_button.setFixedSize(60, 30)
            def on_add_clicked(checked):
                self.add_requested.emit(self.peer_id, self.peer_name)
            self.add_button.clicked.connect(on_add_clicked)
            layout.addWidget(self.add_button)
        else:
            self.setCursor(Qt.PointingHandCursor)
    
    def mousePressEvent(self, event):
        
        if self.is_added and event.button() == Qt.LeftButton:
            self.chat_requested.emit(self.peer_id, self.peer_name)
        super().mousePressEvent(event)

class NotificationsPanel(QFrame):
    suggestion_add_requested = Signal(str, str)  # peer_id, peer_name
    suggestion_chat_requested = Signal(str, str)  # peer_id, peer_name
    
    def __init__(self):
        super().__init__()
        self.setObjectName("RightSidebar") # Đổi tên ID để QSS áp dụng
        self.setMinimumWidth(240)
        self.setMaximumWidth(450)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 15, 15, 15)
        layout.setSpacing(10)

        notify_header = QLabel("Notifications")
        notify_header.setObjectName("SidebarHeader")
        layout.addWidget(notify_header)

        notification_scroll = QScrollArea()
        notification_scroll.setObjectName("SidebarScrollArea")
        notification_scroll.setWidgetResizable(True)
        notification_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded) # Bật cuộn ngang

        notification_content = QWidget()
        notification_content.setObjectName("SidebarScrollContent")
        notification_layout = QVBoxLayout(notification_content) # Layout cho nội dung
        notification_layout.setSpacing(10)
        
        notifications = [
            ("Ankita", "mentioned you in 'Trip to God'", "1 minute ago"),
            ("rakesh.singh", "added you in group 'Study'", "5 mins ago"),
            ("anirudh", "removed you from group 'Riders'", "10 mins ago"),
            ("amit", "mentioned you in public chat", "18 mins ago"),
            ("Ankita", "mentioned you in 'College Gang'", "53 mins ago"),
            ("Vikash.singh", "added you in group 'Designers'", "23 mins ago"),
            ("Ankita", "mentioned you in 'Trip to God'", "1 minute ago"),
            ("rakesh.singh", "added you in group 'Study'", "5 mins ago"),
        ]
        
        for username, text, time_ago in notifications:
            notification_layout.addWidget(NotificationItem(username, text, time_ago))
        
        notification_layout.addStretch() # Đẩy item lên trên
        notification_scroll.setWidget(notification_content) # Gắn content vào scroll
        
        layout.addWidget(notification_scroll, 1) # 1 = co giãn 50%

        sugg_title = QLabel("Suggestions")
        sugg_title.setObjectName("SidebarHeader")
        layout.addWidget(sugg_title) # Thêm header vào layout chính

        suggestion_scroll = QScrollArea()
        suggestion_scroll.setObjectName("SidebarScrollArea")
        suggestion_scroll.setWidgetResizable(True)
        suggestion_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded) # Bật cuộn ngang

        suggestion_content = QWidget()
        suggestion_content.setObjectName("SidebarScrollContent")
        suggestion_layout = QVBoxLayout(suggestion_content) # Layout cho nội dung
        suggestion_layout.setSpacing(10)

        self.suggestion_layout = suggestion_layout
        self.suggestion_content = suggestion_content
        
        self.suggestions = []

        suggestion_scroll.setWidget(suggestion_content) # Gắn content vào scroll
        
        suggestion_content.setVisible(True)
        suggestion_scroll.setVisible(True)

        layout.addWidget(suggestion_scroll, 1)  # 1 = co giãn 50%
        
        self.suggestion_scroll = suggestion_scroll
    
    def load_suggestions(self, suggestions: list):
        
        current_peer_ids = {getattr(w, 'peer_id', None) for w in self.suggestions if hasattr(w, 'peer_id')}
        new_peer_ids = {peer.get('peer_id', '') for peer in suggestions if peer.get('peer_id')}
        
        if current_peer_ids == new_peer_ids and len(suggestions) == len(self.suggestions) and len(suggestions) > 0:
            return
        
        while self.suggestion_layout.count() > 0:
            item = self.suggestion_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()

        self.suggestions = []

        for peer in suggestions:
            peer_id = peer.get('peer_id', '')
            peer_name = peer.get('name', 'Unknown')
            status_text = peer.get('status_text', 'Online')

            is_added = peer.get('is_added', False)
            
            suggestion_item = SuggestionItem(
                name=peer_name,
                status_text=status_text,
                peer_id=peer_id,
                is_added=is_added
            )
            suggestion_item.setVisible(True)
            suggestion_item.setObjectName("SuggestionItem")
            
            if not is_added:
                suggestion_item.add_requested.connect(self._on_suggestion_add_requested)
            else:
                suggestion_item.chat_requested.connect(self._on_suggestion_chat_requested)

            self.suggestion_layout.addWidget(suggestion_item)
            self.suggestions.append(suggestion_item)

        self.suggestion_layout.addStretch()
        self.suggestion_content.setVisible(True)
        self.suggestion_scroll.setVisible(True)
        self.suggestion_layout.update()
    
    def _on_suggestion_add_requested(self, peer_id: str, peer_name: str):
        
        self.suggestion_add_requested.emit(peer_id, peer_name)
    
    def _on_suggestion_chat_requested(self, peer_id: str, peer_name: str):
        
        self.suggestion_chat_requested.emit(peer_id, peer_name)
    
    def remove_suggestion(self, peer_id: str):
        
        if not peer_id:
            return
        
        item_to_remove = None
        widget_to_remove = None
        
        for widget in self.suggestions:
            if hasattr(widget, 'peer_id') and widget.peer_id == peer_id:
                widget_to_remove = widget
                break
        
        if widget_to_remove:
            for i in range(self.suggestion_layout.count()):
                item = self.suggestion_layout.itemAt(i)
                if item and item.widget() == widget_to_remove:
                    item_to_remove = item
                    break
        
        if not item_to_remove:
            for i in range(self.suggestion_layout.count()):
                item = self.suggestion_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if hasattr(widget, 'peer_id') and str(widget.peer_id) == str(peer_id):
                        item_to_remove = item
                        widget_to_remove = widget
                        break
        
        if item_to_remove and widget_to_remove:
            self.suggestion_layout.removeItem(item_to_remove)
            if widget_to_remove in self.suggestions:
                self.suggestions.remove(widget_to_remove)
            widget_to_remove.setParent(None)
            widget_to_remove.deleteLater()
