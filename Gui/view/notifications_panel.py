# notifications_panel.py
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
from PySide6.QtCore import Qt

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
    def __init__(self, name, mutuals_count):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(10)
        avatar = QLabel()
        avatar.setObjectName("NotificationAvatar") # Dùng chung style avatar
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        time_label = QLabel(f"{mutuals_count} Mutuals")
        time_label.setStyleSheet("font-size: 11px; color: #AAA;")
        info_layout.addWidget(name_label)
        info_layout.addWidget(time_label)
        add_btn = QPushButton("Add")
        add_btn.setObjectName("AddButton") # Dùng ID cho QSS
        layout.addWidget(avatar)
        layout.addLayout(info_layout, 1)
        layout.addStretch()
        layout.addWidget(add_btn)

# Class chính của panel (ĐÃ SỬA LẠI)
class NotificationsPanel(QFrame):
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

        suggestions = [
            ("Abhiman Singh", "12"),
            ("Ved Prakash", "15"),
            ("Amit Trivedi", "7"),
            ("Vikash Raj", "2"),
            ("Abhiman Singh", "12"),
            ("Ved Prakash", "15"),
        ]
        
        # Thêm item vào 'suggestion_layout' (BÊN TRONG SCROLL)
        for name, mutuals in suggestions:
            suggestion_layout.addWidget(SuggestionItem(name, mutuals))

        suggestion_layout.addStretch() # Đẩy item lên trên
        suggestion_scroll.setWidget(suggestion_content) # Gắn content vào scroll

        # Thêm ScrollArea (chứ không phải item) vào layout chính
        layout.addWidget(suggestion_scroll, 1)  # 1 = co giãn 50%