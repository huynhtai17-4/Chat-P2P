from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QSize

from ..utils.avatar import load_circular_pixmap


class IncomingCallDialog(QDialog):
    
    call_accepted = Signal()
    call_rejected = Signal()
    
    def __init__(self, caller_name: str, call_type: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Incoming {call_type.title()} Call")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        self.caller_name = caller_name
        self.call_type = call_type
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setAlignment(Qt.AlignCenter)
        
        avatar_label = QLabel()
        avatar_label.setAlignment(Qt.AlignCenter)
        avatar_pixmap = load_circular_pixmap("Gui/assets/images/avatar1.jpg", size=80)
        avatar_label.setPixmap(avatar_pixmap)
        layout.addWidget(avatar_label, alignment=Qt.AlignCenter)
        
        name_label = QLabel(self.caller_name)
        name_label.setObjectName("DialogCallerName")
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)
        
        call_type_text = f"Incoming {self.call_type} call..."
        type_label = QLabel(call_type_text)
        type_label.setObjectName("DialogCallType")
        type_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(type_label)
        
        layout.addStretch()
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)
        
        self.reject_btn = QPushButton()
        self.reject_btn.setObjectName("RejectCallButton")
        self.reject_btn.setIcon(QIcon("Gui/assets/icons/phone.svg"))
        self.reject_btn.setIconSize(QSize(28, 28))
        self.reject_btn.setFixedSize(60, 60)
        self.reject_btn.clicked.connect(self._on_reject)
        
        self.accept_btn = QPushButton()
        self.accept_btn.setObjectName("AcceptCallButton")
        icon_name = "video.svg" if self.call_type == "video" else "phone.svg"
        self.accept_btn.setIcon(QIcon(f"Gui/assets/icons/{icon_name}"))
        self.accept_btn.setIconSize(QSize(28, 28))
        self.accept_btn.setFixedSize(60, 60)
        self.accept_btn.clicked.connect(self._on_accept)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.reject_btn)
        buttons_layout.addWidget(self.accept_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
    
    def _on_accept(self):
        self.call_accepted.emit()
        self.accept()
    
    def _on_reject(self):
        self.call_rejected.emit()
        self.reject()


class OutgoingCallDialog(QDialog):
    
    call_cancelled = Signal()
    
    def __init__(self, callee_name: str, call_type: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{call_type.title()} Call")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        self.callee_name = callee_name
        self.call_type = call_type
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setAlignment(Qt.AlignCenter)
        
        avatar_label = QLabel()
        avatar_label.setAlignment(Qt.AlignCenter)
        avatar_pixmap = load_circular_pixmap("Gui/assets/images/avatar1.jpg", size=80)
        avatar_label.setPixmap(avatar_pixmap)
        layout.addWidget(avatar_label, alignment=Qt.AlignCenter)
        
        name_label = QLabel(self.callee_name)
        name_label.setObjectName("DialogCallerName")
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)
        
        self.status_label = QLabel("Calling...")
        self.status_label.setObjectName("DialogStatus")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        self.cancel_btn = QPushButton()
        self.cancel_btn.setObjectName("CancelCallButton")
        self.cancel_btn.setIcon(QIcon("Gui/assets/icons/phone.svg"))
        self.cancel_btn.setIconSize(QSize(28, 28))
        self.cancel_btn.setFixedSize(60, 60)
        self.cancel_btn.clicked.connect(self._on_cancel)
        
        layout.addWidget(self.cancel_btn, alignment=Qt.AlignCenter)
    
    def _on_cancel(self):
        self.call_cancelled.emit()
        self.reject()
    
    def set_status(self, status: str):
        self.status_label.setText(status)

