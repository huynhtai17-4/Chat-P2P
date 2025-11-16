# chat_item.py
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor # [THÊM MỚI] Import QColor

from ..utils.elide_label import ElideLabel  # Thay 'elide_label' bằng tên file thực tế nếu khác

class ChatItemWidget(QFrame):
    """
    Component cho MỖI MỤC trong danh sách chat bên trái.
    """
    def __init__(self, name, message, time, unread_count=None, is_active=False):
        super().__init__()
       
        self.name_label = None
        self.message_label = None
        self.time_label = None

        # Dùng setObjectName để QSS có thể áp dụng style
        if is_active:
            self.setObjectName("ChatItemWidgetActive")
           
            # [THÊM MỚI] Thêm hiệu ứng đổ bóng để làm nổi bật
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(15)
            shadow.setOffset(0, 3) # Hơi đổ bóng xuống dưới
            shadow.setColor(QColor(0, 0, 0, 80)) # Màu đen, 30% độ mờ
            self.setGraphicsEffect(shadow)
           
        else:
            self.setObjectName("ChatItemWidget")
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)
        # 1. Avatar (Placeholder)
        avatar = QLabel()
        avatar.setObjectName("AvatarLabel")
       
        # 2. Cột nội dung (Tên + Tin nhắn)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
       
        name_label = QLabel(name)
        name_label.setObjectName("NameLabel")
       
        # Sử dụng ElideLabel thay vì QLabel để hỗ trợ elide với dấu "..."
        message_label = ElideLabel(message)
        message_label.setObjectName("MessageLabel")
        message_label.setElideMode(Qt.ElideRight)  # Elide bên phải (mặc định)
       
        text_layout.addWidget(name_label)
        text_layout.addWidget(message_label)
        text_layout.addStretch()
        # 3. Cột thời gian (Thời gian + Số tin chưa đọc)
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
            time_layout.addStretch() # Thêm stretch nếu không có unread
        # Thêm vào layout chính
        main_layout.addWidget(avatar)
        main_layout.addLayout(text_layout, 1) # 1 = co giãn
        main_layout.addLayout(time_layout)

    def set_selected(self, selected):
        """Thiết lập trạng thái selected cho chat item"""
        if selected:
            self.setObjectName("ChatItemWidgetActive")
            # Thêm hiệu ứng shadow
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(15)
            shadow.setOffset(0, 3)
            shadow.setColor(QColor(0, 0, 0, 80))
            self.setGraphicsEffect(shadow)
        else:
            self.setObjectName("ChatItemWidget")
            # Xóa hiệu ứng shadow
            self.setGraphicsEffect(None)
        
        # Force refresh style
        self.style().unpolish(self)
        self.style().polish(self)
        
        # Refresh tất cả các label con
        for child in self.findChildren(QLabel):
            child.style().unpolish(child)
            child.style().polish(child)