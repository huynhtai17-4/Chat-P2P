from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

class MessageBubble(QLabel):
    def __init__(self, text, is_sender=True, time_str=None):
        if time_str:
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            
            super().__init__(text)
            self.setWordWrap(True)  # Tự động xuống dòng
            
            time_label = QLabel(time_str)
            time_label.setObjectName("MessageTimestamp")
            time_label.setAlignment(Qt.AlignRight if is_sender else Qt.AlignLeft)
            time_label.setStyleSheet("font-size: 10px; color: #999; padding: 2px 5px;")
            
            layout.addWidget(self)
            layout.addWidget(time_label)
            
            self._container = container
        else:
            super().__init__(text)
            self.setWordWrap(True)  # Tự động xuống dòng
            self._container = None
        
        if is_sender:
            self.setObjectName("MessageBubbleSelf")
        else:
            self.setObjectName("MessageBubbleOther")

        self.setProperty("class", "MessageBubble")
    
    def get_widget(self):
        
        return self._container if self._container else self
