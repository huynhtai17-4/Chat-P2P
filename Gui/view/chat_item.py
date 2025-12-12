from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ..utils.elide_label import ElideLabel

class ChatItemWidget(QFrame):
    
    def __init__(self, name, message, time, unread_count=None, is_active=False, avatar_path=None):
        super().__init__()
       
        self.name_label = None
        self.message_label = None
        self.time_label = None

        if is_active:
            self.setObjectName("ChatItemWidgetActive")
           
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(15)
            shadow.setOffset(0, 3)
            shadow.setColor(QColor(0, 0, 0, 80))
            self.setGraphicsEffect(shadow)
           
        else:
            self.setObjectName("ChatItemWidget")
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)
        avatar_container = QFrame()
        avatar_container.setObjectName("AvatarContainer")
        avatar_layout = QVBoxLayout(avatar_container)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.setSpacing(0)
        
        self.avatar = QLabel()
        self.avatar.setObjectName("AvatarLabel")
        self.avatar.setFixedSize(40, 40)
        from ..utils.avatar import load_circular_pixmap
        import os
        
        if avatar_path and os.path.exists(avatar_path):
            pixmap = load_circular_pixmap(avatar_path, size=40)
        else:
            default_avatar_path = "Gui/assets/images/avatar1.jpg"
            pixmap = load_circular_pixmap(default_avatar_path, size=40)
        self.avatar.setPixmap(pixmap)
        self.avatar.setScaledContents(True)
        avatar_layout.addWidget(self.avatar)
        
        self.online_indicator = QLabel()
        self.online_indicator.setObjectName("OnlineIndicator")
        self.online_indicator.setFixedSize(12, 12)
        self.online_indicator.setVisible(False)
        avatar_layout.addWidget(self.online_indicator, 0, Qt.AlignRight | Qt.AlignBottom)
       
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
       
        name_label = QLabel(name)
        name_label.setObjectName("NameLabel")
       
        message_label = ElideLabel(message)
        message_label.setObjectName("MessageLabel")
        message_label.setElideMode(Qt.ElideRight)
       
        text_layout.addWidget(name_label)
        text_layout.addWidget(message_label)
        text_layout.addStretch()
        time_layout = QVBoxLayout()
        time_layout.setSpacing(5)
        time_layout.setAlignment(Qt.AlignTop | Qt.AlignRight)
       
        time_label = QLabel(time)
        time_label.setObjectName("TimeLabel")
        time_layout.addWidget(time_label)
        if unread_count and unread_count > 0:
            count_label = QLabel(str(unread_count))
            count_label.setObjectName("UnreadCountLabel")
            count_label.setAlignment(Qt.AlignCenter)
            time_layout.addWidget(count_label, 0, Qt.AlignRight)
        else:
            time_layout.addStretch()
        main_layout.addWidget(avatar_container)
        main_layout.addLayout(text_layout, 1)
        main_layout.addLayout(time_layout)
        
        self.contact_name = name
        self.last_message = message
        self.time_label = time
        self.unread_count = unread_count
        self.is_online = False

    def set_selected(self, selected):
        
        if selected:
            self.setObjectName("ChatItemWidgetActive")
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(15)
            shadow.setOffset(0, 3)
            shadow.setColor(QColor(0, 0, 0, 80))
            self.setGraphicsEffect(shadow)
        else:
            self.setObjectName("ChatItemWidget")
            self.setGraphicsEffect(None)
        
        self.style().unpolish(self)
        self.style().polish(self)
        
        for child in self.findChildren(QLabel):
            child.style().unpolish(child)
            child.style().polish(child)
    
    def set_online_status(self, is_online: bool):
        
        self.is_online = is_online
        if hasattr(self, 'online_indicator'):
            self.online_indicator.setVisible(is_online)
    
    def set_avatar(self, avatar_path: str = None):
        from ..utils.avatar import load_circular_pixmap
        import os
        
        if avatar_path and os.path.exists(avatar_path):
            pixmap = load_circular_pixmap(avatar_path, size=40)
        else:
            default_path = "Gui/assets/images/avatar1.jpg"
            pixmap = load_circular_pixmap(default_path, size=40)
        
        if hasattr(self, 'avatar'):
            self.avatar.setPixmap(pixmap)
