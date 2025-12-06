# message_bubble.py
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

class MessageBubble(QLabel):
    def __init__(self, text, is_sender=True, time_str=None):
        # If time_str is provided, create a widget with message and timestamp
        if time_str:
            # Create a container widget
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            
            # Message text
            super().__init__(text)
            self.setWordWrap(True)  # Tự động xuống dòng
            
            # Timestamp label
            time_label = QLabel(time_str)
            time_label.setObjectName("MessageTimestamp")
            time_label.setAlignment(Qt.AlignRight if is_sender else Qt.AlignLeft)
            time_label.setStyleSheet("font-size: 10px; color: #999; padding: 2px 5px;")
            
            # Add to layout
            layout.addWidget(self)
            layout.addWidget(time_label)
            
            # Store container for later use
            self._container = container
        else:
            # No timestamp - use simple label
            super().__init__(text)
            self.setWordWrap(True)  # Tự động xuống dòng
            self._container = None
        
        # Dùng setObjectName và setProperty để QSS toàn cục xử lý
        if is_sender:
            self.setObjectName("MessageBubbleSelf")
        else:
            self.setObjectName("MessageBubbleOther")

        # Đặt class chung
        self.setProperty("class", "MessageBubble")
    
    def get_widget(self):
        """Get the widget to add to layout (container if timestamp exists, self otherwise)"""
        return self._container if self._container else self