from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QCheckBox, QWidget
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap
from app.user_manager import UserManager, User

class LoginWindow(QDialog):

    login_successful = Signal(User)
    register_requested = Signal()
    
    def __init__(self, user_manager: UserManager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        
        self.setWindowTitle("Chat P2P - Login")
        self.setFixedSize(520, 580)
        self.setModal(True)
        self.setStyleSheet("QDialog { background-color: #4A90E2; }")
        
        self._setup_ui()
    
    def _setup_ui(self):
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 60, 40, 60)
        main_layout.setAlignment(Qt.AlignCenter)
        
        card = QWidget()
        card.setObjectName("LoginCard")
        card.setFixedSize(440, 460)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(50, 40, 50, 40)
        card_layout.setSpacing(0)
        
        title = QLabel("Login")
        title.setObjectName("CardTitle")
        title.setAlignment(Qt.AlignLeft)
        card_layout.addWidget(title)
        card_layout.addSpacing(40)
        
        email_container = QHBoxLayout()
        email_container.setSpacing(15)
        
        email_icon = QLabel()
        email_icon.setPixmap(QPixmap("Gui/assets/icons/mail.svg").scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        email_icon.setObjectName("FieldIcon")
        email_container.addWidget(email_icon)
        
        self.username_input = QLineEdit()
        self.username_input.setObjectName("UnderlineInput")
        self.username_input.setPlaceholderText("Enter your email")
        self.username_input.setMaxLength(50)
        email_container.addWidget(self.username_input, 1)
        
        card_layout.addLayout(email_container)
        card_layout.addSpacing(30)
        
        password_container = QHBoxLayout()
        password_container.setSpacing(15)
        
        password_icon = QLabel()
        password_icon.setPixmap(QPixmap("Gui/assets/icons/lock.svg").scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        password_icon.setObjectName("FieldIcon")
        password_container.addWidget(password_icon)
        
        self.password_input = QLineEdit()
        self.password_input.setObjectName("UnderlineInput")
        self.password_input.setPlaceholderText("Confirm a password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMaxLength(50)
        self.password_input.returnPressed.connect(self._login)
        password_container.addWidget(self.password_input, 1)
        
        self.eye_icon = QLabel()
        self.eye_icon.setPixmap(QPixmap("Gui/assets/icons/eye_off.svg").scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.eye_icon.setObjectName("EyeIcon")
        self.eye_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.eye_icon.mousePressEvent = lambda e: self._toggle_password_visibility()
        password_container.addWidget(self.eye_icon)
        
        card_layout.addLayout(password_container)
        card_layout.addSpacing(25)
        
        options_layout = QHBoxLayout()

        options_layout.addStretch()
        
        forgot_link = QPushButton("Forgot password?")
        forgot_link.setObjectName("TextLink")
        forgot_link.setCursor(Qt.CursorShape.PointingHandCursor)
        options_layout.addWidget(forgot_link)
        
        card_layout.addLayout(options_layout)
        card_layout.addSpacing(30)
        
        self.login_btn = QPushButton("Login")
        self.login_btn.setObjectName("ModernPrimaryButton")
        self.login_btn.setFixedHeight(50)
        self.login_btn.clicked.connect(self._login)
        card_layout.addWidget(self.login_btn)
        
        card_layout.addSpacing(25)
        
        signup_layout = QHBoxLayout()
        signup_layout.setAlignment(Qt.AlignCenter)
        
        self.register_link = QPushButton("Signup")
        self.register_link.setObjectName("ColoredLink")
        self.register_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.register_link.clicked.connect(self._go_to_register)
        signup_layout.addWidget(self.register_link)
        
        card_layout.addLayout(signup_layout)
        
        main_layout.addWidget(card)
        
        self.username_input.setFocus()
    
    def _login(self):
        
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username:
            QMessageBox.warning(self, "Error", "Please enter your username/email")
            self.username_input.setFocus()
            return
        
        if not password:
            QMessageBox.warning(self, "Error", "Please enter your password")
            self.password_input.setFocus()
            return
        
        success, user, message = self.user_manager.login(username, password)
        
        if success:
            print(f"[Login] Successful: {user.display_name}")
            self.login_successful.emit(user)
            self.accept()
        else:
            QMessageBox.warning(self, "Login Failed", message)
            self.password_input.clear()
            self.password_input.setFocus()
    
    def _go_to_register(self):
        
        self.register_requested.emit()
        self.close()
    
    def set_username(self, username: str):
        
        self.username_input.setText(username)
        self.password_input.setFocus()
    
    def _toggle_password_visibility(self):
        
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.eye_icon.setPixmap(QPixmap("Gui/assets/icons/eye_on.svg").scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.eye_icon.setPixmap(QPixmap("Gui/assets/icons/eye_off.svg").scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
