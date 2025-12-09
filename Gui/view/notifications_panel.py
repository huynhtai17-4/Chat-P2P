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
        
        label.setStyleSheet("font-size: 13px; color: #555;")
        time_label = QLabel(time_ago)
        time_label.setStyleSheet("color: #AAA; font-size: 11px;")
        text_layout.addWidget(label)
        text_layout.addWidget(time_label)
        layout.addWidget(avatar)
        layout.addLayout(text_layout, 1)

class NotificationsPanel(QFrame):
    add_friend_requested = Signal(str, int)  # Signal(ip: str, port: int)
    
    def __init__(self):
        super().__init__()
        self.setObjectName("RightSidebar")
        self.setMinimumWidth(240)
        self.setMaximumWidth(450)
        self.setMinimumHeight(500)
        
        # Main layout - vertical
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 15, 15, 15)
        main_layout.setSpacing(10)

        # 1) Notifications Header
        notify_header = QLabel("Notifications")
        notify_header.setObjectName("SidebarHeader")
        main_layout.addWidget(notify_header)

        # 2) Notifications ScrollArea (only contains notifications)
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
        
        # Add scroll area with stretch factor so it takes available space
        main_layout.addWidget(notification_scroll, 1)

        # 3) Section Divider (spacing)
        main_layout.addSpacing(10)

        # 4) User Network Info (Your IPs/Port)
        network_info_container = QWidget()
        network_info_layout = QVBoxLayout(network_info_container)
        network_info_layout.setContentsMargins(0, 0, 0, 0)
        network_info_layout.setSpacing(3)
        
        # LAN IP (for network)
        self.lan_ip_label = QLabel("LAN IP: --")
        self.lan_ip_label.setStyleSheet("font-size: 12px; color: #2196F3; font-weight: bold;")
        network_info_layout.addWidget(self.lan_ip_label)
        
        # Port
        self.port_label = QLabel("Your Port: --")
        self.port_label.setStyleSheet("font-size: 12px; color: #2196F3; font-weight: bold;")
        network_info_layout.addWidget(self.port_label)
        
        main_layout.addWidget(network_info_container)
        main_layout.addSpacing(10)

        # 5) Add Friend by IP Header
        add_friend_title = QLabel("Add Friend by IP")
        add_friend_title.setObjectName("SidebarHeader")
        main_layout.addWidget(add_friend_title)

        # 6-8) Add Friend Form (IP Input, Port Input, Button)
        # Create container widget for Add Friend section
        add_friend_container = QWidget()
        add_friend_layout = QVBoxLayout(add_friend_container)
        add_friend_layout.setContentsMargins(0, 0, 0, 0)
        add_friend_layout.setSpacing(8)

        peer_ip_label = QLabel("Peer IP:")
        peer_ip_label.setStyleSheet("font-size: 12px; color: #555;")
        add_friend_layout.addWidget(peer_ip_label)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("e.g., 192.168.1.10")
        self.ip_input.setObjectName("AddFriendInput")
        add_friend_layout.addWidget(self.ip_input)

        peer_port_label = QLabel("Port:")
        peer_port_label.setStyleSheet("font-size: 12px; color: #555;")
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

        # Add container to main layout (no stretch - fixed at bottom)
        main_layout.addWidget(add_friend_container)
    
    def set_user_network_info(self, lan_ip: str, port: int):
        """Set the user's network info display."""
        # Show LAN IP
        if not lan_ip or lan_ip.startswith("127."):
            self.lan_ip_label.setText("LAN IP: Not available (no network)")
            self.lan_ip_label.setStyleSheet("font-size: 11px; color: #999;")
        else:
            self.lan_ip_label.setText(f"LAN IP: {lan_ip}")
            self.lan_ip_label.setStyleSheet("font-size: 12px; color: #2196F3; font-weight: bold;")
        
        # Show port
        self.port_label.setText(f"Port: {port}")
    
    def _on_add_friend_clicked(self):
        """Handle Add Friend button click"""
        ip = self.ip_input.text().strip()
        port_str = self.port_input.text().strip()
        
        print(f"[NotificationsPanel] Add Friend clicked: IP={ip}, Port={port_str}")
        
        if not ip:
            print("[NotificationsPanel] IP is empty, returning")
            return
        
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                print(f"[NotificationsPanel] Port {port} out of range, returning")
                return
        except ValueError:
            print(f"[NotificationsPanel] Invalid port value: {port_str}")
            return
        
        print(f"[NotificationsPanel] About to emit signal with: IP={ip} (type={type(ip)}), Port={port} (type={type(port)})")
        print(f"[NotificationsPanel] Signal object: {self.add_friend_requested}")
        print(f"[NotificationsPanel] Calling emit({repr(ip)}, {repr(port)})")
        try:
            result = self.add_friend_requested.emit(ip, port)
            print(f"[NotificationsPanel] Signal emitted successfully, result={result}")
        except Exception as e:
            print(f"[NotificationsPanel] ERROR emitting signal: {e}")
            import traceback
            traceback.print_exc()
        
        # Clear inputs after adding
        self.ip_input.clear()
        self.port_input.clear()
