# message_bubble.py
from PySide6.QtWidgets import QLabel

class MessageBubble(QLabel):
    def __init__(self, text, is_sender=True):
        super().__init__(text)
        self.setWordWrap(True) # Tự động xuống dòng
        
        # Dùng setObjectName và setProperty để QSS toàn cục xử lý
        if is_sender:
            self.setObjectName("MessageBubbleSelf")
        else:
            self.setObjectName("MessageBubbleOther")

        # Đặt class chung
        self.setProperty("class", "MessageBubble")