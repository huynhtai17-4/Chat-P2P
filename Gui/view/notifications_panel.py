# notifications_panel.py
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
from PySide6.QtCore import Qt, Signal

# Các class con (component) cho các mục thông báo
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
        
        # (Giữ RichText để cho phép cuộn ngang)
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
    # Signal khi click nút Add
    add_requested = Signal(str, str)  # peer_id, peer_name
    # Signal khi click vào item để chat (sau khi đã add)
    chat_requested = Signal(str, str)  # peer_id, peer_name
    
    def __init__(self, name, status_text="Online", peer_id=None, is_added=False):
        super().__init__()
        self.peer_id = peer_id
        self.peer_name = name
        self.is_added = is_added
        
        # Set object name and ensure visible
        self.setObjectName("SuggestionItem")
        self.setVisible(True)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(10)
        
        # Avatar với online indicator
        avatar_container = QFrame()
        avatar_container.setObjectName("AvatarContainer")
        avatar_layout = QVBoxLayout(avatar_container)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.setSpacing(0)
        
        avatar = QLabel()
        avatar.setObjectName("NotificationAvatar")
        avatar_layout.addWidget(avatar)
        
        # Online indicator
        self.online_indicator = QLabel()
        self.online_indicator.setObjectName("OnlineIndicator")
        self.online_indicator.setFixedSize(12, 12)
        self.online_indicator.setVisible(True)
        avatar_layout.addWidget(self.online_indicator, 0, Qt.AlignRight | Qt.AlignBottom)
        
        # Text layout
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        # Tên user
        txt = f"<b>@{name}</b>"
        label = QLabel(txt)
        label.setWordWrap(False)
        label.setTextFormat(Qt.RichText)
        label.setStyleSheet("font-size: 13px; color: #555;")
        
        # Status
        status_label = QLabel(status_text)
        status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
        
        text_layout.addWidget(label)
        text_layout.addWidget(status_label)
        
        layout.addWidget(avatar_container)
        layout.addLayout(text_layout, 1)
        
        # Nút Add hoặc Chat
        if not is_added:
            # Hiển thị nút Add cho peer chưa được add
            self.add_button = QPushButton("Add")
            self.add_button.setObjectName("AddButton")
            self.add_button.setFixedSize(60, 30)
            self.add_button.clicked.connect(lambda: self.add_requested.emit(self.peer_id, self.peer_name))
            layout.addWidget(self.add_button)
        else:
            # Đã add rồi, có thể click để chat
            self.setCursor(Qt.PointingHandCursor)
    
    def mousePressEvent(self, event):
        """Handle click on suggestion item (only if already added)"""
        if self.is_added and event.button() == Qt.LeftButton:
            self.chat_requested.emit(self.peer_id, self.peer_name)
        super().mousePressEvent(event)

# Class chính của panel (ĐÃ SỬA LẠI)
class NotificationsPanel(QFrame):
    # Signal khi click Add trên suggestion
    suggestion_add_requested = Signal(str, str)  # peer_id, peer_name
    # Signal khi click Chat trên suggestion (sau khi đã add)
    suggestion_chat_requested = Signal(str, str)  # peer_id, peer_name
    
    def __init__(self):
        super().__init__()
        self.setObjectName("RightSidebar") # Đổi tên ID để QSS áp dụng
        self.setMinimumWidth(240)
        self.setMaximumWidth(450)
        self.setMinimumHeight(500)
        
        # Layout CHÍNH của cột
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 15, 15, 15)
        layout.setSpacing(10)
        
        # --- 1. Phần Notifications ---
        
        # Thêm header "Notifications" vào layout chính
        notify_header = QLabel("Notifications")
        notify_header.setObjectName("SidebarHeader")
        layout.addWidget(notify_header)

        # Tạo ScrollArea cho Notifications
        notification_scroll = QScrollArea()
        notification_scroll.setObjectName("SidebarScrollArea")
        notification_scroll.setWidgetResizable(True)
        notification_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded) # Bật cuộn ngang

        # Tạo Content và Layout BÊN TRONG
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
        
        # Thêm item vào 'notification_layout' (BÊN TRONG SCROLL)
        for username, text, time_ago in notifications:
            notification_layout.addWidget(NotificationItem(username, text, time_ago))
        
        notification_layout.addStretch() # Đẩy item lên trên
        notification_scroll.setWidget(notification_content) # Gắn content vào scroll
        
        # Thêm ScrollArea (chứ không phải item) vào layout chính
        layout.addWidget(notification_scroll, 1) # 1 = co giãn 50%

        # --- 2. Phần Suggestions ---
        
        # Thêm header "Suggestions" vào layout chính
        sugg_title = QLabel("Suggestions")
        sugg_title.setObjectName("SidebarHeader")
        layout.addWidget(sugg_title) # Thêm header vào layout chính

        # Tạo ScrollArea cho Suggestions
        suggestion_scroll = QScrollArea()
        suggestion_scroll.setObjectName("SidebarScrollArea")
        suggestion_scroll.setWidgetResizable(True)
        suggestion_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded) # Bật cuộn ngang

        # Tạo Content và Layout BÊN TRONG
        suggestion_content = QWidget()
        suggestion_content.setObjectName("SidebarScrollContent")
        suggestion_layout = QVBoxLayout(suggestion_content) # Layout cho nội dung
        suggestion_layout.setSpacing(10)

        # Suggestions sẽ được cung cấp từ lớp điều khiển bên ngoài
        self.suggestion_layout = suggestion_layout
        self.suggestion_content = suggestion_content
        
        # Store reference để có thể update sau
        self.suggestions = []

        # Don't add stretch here - will be added when loading suggestions
        suggestion_scroll.setWidget(suggestion_content) # Gắn content vào scroll
        
        # Make sure content is visible
        suggestion_content.setVisible(True)
        suggestion_scroll.setVisible(True)

        # Thêm ScrollArea (chứ không phải item) vào layout chính
        layout.addWidget(suggestion_scroll, 1)  # 1 = co giãn 50%
        
        # Store references
        self.suggestion_scroll = suggestion_scroll
    
    def load_suggestions(self, suggestions: list):
        """Hiển thị danh sách gợi ý chat."""
        # Check if suggestions actually changed to avoid unnecessary refresh
        current_peer_ids = {getattr(w, 'peer_id', None) for w in self.suggestions if hasattr(w, 'peer_id')}
        new_peer_ids = {peer.get('peer_id', '') for peer in suggestions if peer.get('peer_id')}
        
        # Only refresh if suggestions actually changed
        if current_peer_ids == new_peer_ids and len(suggestions) == len(self.suggestions):
            # Same suggestions, skip refresh to prevent flickering
            return
        
        # Clear existing suggestions
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

            # Check if peer is already added (is_added flag)
            is_added = peer.get('is_added', False)
            
            suggestion_item = SuggestionItem(
                name=peer_name,
                status_text=status_text,
                peer_id=peer_id,
                is_added=is_added
            )
            suggestion_item.setVisible(True)
            suggestion_item.setObjectName("SuggestionItem")
            
            # Connect signals
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
        """Handle khi click nút Add trên suggestion"""
        # Emit signal để main_window xử lý
        self.suggestion_add_requested.emit(peer_id, peer_name)
    
    def _on_suggestion_chat_requested(self, peer_id: str, peer_name: str):
        """Handle khi click nút Chat trên suggestion (sau khi đã add)"""
        # Emit signal để main_window xử lý
        self.suggestion_chat_requested.emit(peer_id, peer_name)
    
    def remove_suggestion(self, peer_id: str):
        """
        Remove a suggestion item by peer_id.
        This is called when peer becomes a friend or request is sent.
        
        Args:
            peer_id: The peer_id to remove
        """
        if not peer_id:
            return
        
        # Find and remove the suggestion item with matching peer_id
        item_to_remove = None
        for i in range(self.suggestion_layout.count()):
            item = self.suggestion_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # Check if this is a SuggestionItem with matching peer_id
                if hasattr(widget, 'peer_id') and widget.peer_id == peer_id:
                    item_to_remove = item
                    break
        
        if item_to_remove:
            widget = item_to_remove.widget()
            if widget:
                # Remove from layout
                self.suggestion_layout.removeItem(item_to_remove)
                # Clean up widget
                widget.setParent(None)
                widget.deleteLater()
                # Remove from suggestions list
                if widget in self.suggestions:
                    self.suggestions.remove(widget)