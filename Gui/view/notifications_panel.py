from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget, QLineEdit
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
        label.setObjectName("NotificationTextLabel")
        
        time_label = QLabel(time_ago)
        time_label.setObjectName("NotificationTimeLabel")
        text_layout.addWidget(label)
        text_layout.addWidget(time_label)
        layout.addWidget(avatar)
        layout.addLayout(text_layout, 1)

class NotificationsPanel(QFrame):
    add_friend_requested = Signal(str, int)
    
    def __init__(self):
        super().__init__()
        self.setObjectName("RightSidebar")
        self.setMinimumWidth(240)
        self.setMaximumWidth(450)
        self.setMinimumHeight(500)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 15, 15, 15)
        main_layout.setSpacing(10)

        notify_header = QLabel("Notifications")
        notify_header.setObjectName("SidebarHeader")
        main_layout.addWidget(notify_header)

        notification_scroll = QScrollArea()
        notification_scroll.setObjectName("SidebarScrollArea")
        notification_scroll.setWidgetResizable(True)
        notification_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        notification_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        notification_content = QWidget()
        notification_content.setObjectName("SidebarScrollContent")
        notification_layout = QVBoxLayout(notification_content)
        notification_layout.setContentsMargins(0, 0, 0, 0)
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
        
        notification_layout.addStretch()
        notification_scroll.setWidget(notification_content)
        
        main_layout.addWidget(notification_scroll, 1)

        main_layout.addSpacing(10)

        network_info_container = QWidget()
        network_info_layout = QVBoxLayout(network_info_container)
        network_info_layout.setContentsMargins(0, 0, 0, 0)
        network_info_layout.setSpacing(3)
        
        self.lan_ip_label = QLabel("LAN IP: --")
        self.lan_ip_label.setObjectName("NetworkInfoLabel")
        network_info_layout.addWidget(self.lan_ip_label)
        
        self.port_label = QLabel("Your Port: --")
        self.port_label.setObjectName("NetworkInfoLabel")
        network_info_layout.addWidget(self.port_label)
        
        main_layout.addWidget(network_info_container)
        main_layout.addSpacing(10)

        add_friend_title = QLabel("Add Friend by IP")
        add_friend_title.setObjectName("SidebarHeader")
        main_layout.addWidget(add_friend_title)

        add_friend_container = QWidget()
        add_friend_layout = QVBoxLayout(add_friend_container)
        add_friend_layout.setContentsMargins(0, 0, 0, 0)
        add_friend_layout.setSpacing(8)

        peer_ip_label = QLabel("Peer IP:")
        peer_ip_label.setObjectName("FormLabel")
        add_friend_layout.addWidget(peer_ip_label)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("e.g., 192.168.1.10")
        self.ip_input.setObjectName("AddFriendInput")
        add_friend_layout.addWidget(self.ip_input)

        peer_port_label = QLabel("Port:")
        peer_port_label.setObjectName("FormLabel")
        add_friend_layout.addWidget(peer_port_label)

        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("55000-55199")
        self.port_input.setObjectName("AddFriendInput")
        add_friend_layout.addWidget(self.port_input)

        add_friend_btn = QPushButton("Add Friend")
        add_friend_btn.setObjectName("AddFriendButton")
        add_friend_btn.setFixedHeight(35)
        add_friend_btn.clicked.connect(self._on_add_friend_clicked)
        add_friend_layout.addWidget(add_friend_btn)

        main_layout.addWidget(add_friend_container)
    
    def set_user_network_info(self, lan_ip: str, port: int):
        if not lan_ip or lan_ip.startswith("127."):
            self.lan_ip_label.setText("LAN IP: Not available (no network)")
            self.lan_ip_label.setObjectName("NetworkInfoLabelInactive")
        else:
            self.lan_ip_label.setText(f"LAN IP: {lan_ip}")
            self.lan_ip_label.setObjectName("NetworkInfoLabel")
        
        self.port_label.setText(f"Port: {port}")
    
    def _on_add_friend_clicked(self):
        ip = self.ip_input.text().strip()
        port_str = self.port_input.text().strip()
        
        if not ip:
            return
        
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                return
        except ValueError:
            return
        
        self.add_friend_requested.emit(ip, port)
        
        self.ip_input.clear()
        self.port_input.clear()
