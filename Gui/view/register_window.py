from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QCheckBox, QWidget
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon
from app.user_manager import UserManager
from ..utils.avatar import load_circular_pixmap
import os

class RegisterWindow(QDialog):

    registration_successful = Signal(str, str)
    
    def __init__(self, user_manager: UserManager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.selected_avatar_path = None
        
        self.setWindowTitle("Chat P2P - Register")
        self.setFixedSize(520, 750)
        self.setModal(True)
        self.setStyleSheet("QDialog { background-color: #4A90E2; }")
        
        self._setup_ui()
    
    def _setup_ui(self):
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setAlignment(Qt.AlignCenter)
        
        card = QWidget()
        card.setObjectName("LoginCard")
        card.setFixedSize(440, 670)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(50, 35, 50, 35)
        card_layout.setSpacing(0)
        
        title = QLabel("Registration")
        title.setObjectName("CardTitle")
        title.setAlignment(Qt.AlignLeft)
        card_layout.addWidget(title)
        card_layout.addSpacing(25)
        
        avatar_container = QHBoxLayout()
        avatar_container.setAlignment(Qt.AlignCenter)
        
        avatar_wrapper = QVBoxLayout()
        avatar_wrapper.setSpacing(8)
        avatar_wrapper.setAlignment(Qt.AlignCenter)
        
        self.avatar_label = QLabel()
        self.avatar_label.setObjectName("AvatarPreview")
        self.avatar_label.setFixedSize(100, 100)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self._set_default_avatar()
        avatar_wrapper.addWidget(self.avatar_label, 0, Qt.AlignCenter)
        
        self.upload_btn = QPushButton("Choose Avatar")
        self.upload_btn.setObjectName("UploadAvatarButton")
        self.upload_btn.setFixedSize(140, 35)
        self.upload_btn.clicked.connect(self._choose_avatar)
        avatar_wrapper.addWidget(self.upload_btn, 0, Qt.AlignCenter)
        
        avatar_container.addLayout(avatar_wrapper)
        
        card_layout.addLayout(avatar_container)
        card_layout.addSpacing(25)
        
        displayname_container = QHBoxLayout()
        displayname_container.setSpacing(15)
        
        displayname_icon = QLabel()
        displayname_icon.setPixmap(QPixmap("Gui/assets/icons/user.svg").scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        displayname_icon.setObjectName("FieldIcon")
        displayname_container.addWidget(displayname_icon)
        
        self.display_name_input = QLineEdit()
        self.display_name_input.setObjectName("UnderlineInput")
        self.display_name_input.setPlaceholderText("Enter your name")
        self.display_name_input.setMaxLength(20)
        displayname_container.addWidget(self.display_name_input, 1)
        
        card_layout.addLayout(displayname_container)
        card_layout.addSpacing(20)
        
        username_container = QHBoxLayout()
        username_container.setSpacing(15)
        
        username_icon = QLabel()
        username_icon.setPixmap(QPixmap("Gui/assets/icons/mail.svg").scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        username_icon.setObjectName("FieldIcon")
        username_container.addWidget(username_icon)
        
        self.username_input = QLineEdit()
        self.username_input.setObjectName("UnderlineInput")
        self.username_input.setPlaceholderText("Enter your email")
        self.username_input.setMaxLength(30)
        username_container.addWidget(self.username_input, 1)
        
        card_layout.addLayout(username_container)
        card_layout.addSpacing(20)
        
        password_container = QHBoxLayout()
        password_container.setSpacing(15)
        
        password_icon = QLabel()
        password_icon.setPixmap(QPixmap("Gui/assets/icons/lock.svg").scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        password_icon.setObjectName("FieldIcon")
        password_container.addWidget(password_icon)
        
        self.password_input = QLineEdit()
        self.password_input.setObjectName("UnderlineInput")
        self.password_input.setPlaceholderText("Create a password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMaxLength(50)
        password_container.addWidget(self.password_input, 1)
        
        self.eye_icon1 = QLabel()
        self.eye_icon1.setPixmap(QPixmap("Gui/assets/icons/eye_off.svg").scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.eye_icon1.setObjectName("EyeIcon")
        self.eye_icon1.setCursor(Qt.CursorShape.PointingHandCursor)
        self.eye_icon1.mousePressEvent = lambda e: self._toggle_password_visibility(1)
        password_container.addWidget(self.eye_icon1)
        
        card_layout.addLayout(password_container)
        card_layout.addSpacing(20)
        
        confirm_container = QHBoxLayout()
        confirm_container.setSpacing(15)
        
        confirm_icon = QLabel()
        confirm_icon.setPixmap(QPixmap("Gui/assets/icons/lock.svg").scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        confirm_icon.setObjectName("FieldIcon")
        confirm_container.addWidget(confirm_icon)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setObjectName("UnderlineInput")
        self.confirm_password_input.setPlaceholderText("Confirm a password")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setMaxLength(50)
        self.confirm_password_input.returnPressed.connect(self._register)
        confirm_container.addWidget(self.confirm_password_input, 1)
        
        self.eye_icon2 = QLabel()
        self.eye_icon2.setPixmap(QPixmap("Gui/assets/icons/eye_off.svg").scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.eye_icon2.setObjectName("EyeIcon")
        self.eye_icon2.setCursor(Qt.CursorShape.PointingHandCursor)
        self.eye_icon2.mousePressEvent = lambda e: self._toggle_password_visibility(2)
        confirm_container.addWidget(self.eye_icon2)
        
        card_layout.addLayout(confirm_container)
        card_layout.addSpacing(25)

        self.register_btn = QPushButton("Register")
        self.register_btn.setObjectName("ModernPrimaryButton")
        self.register_btn.setFixedHeight(50)
        self.register_btn.clicked.connect(self._register)
        card_layout.addWidget(self.register_btn)
        
        card_layout.addSpacing(20)
        
        login_layout = QHBoxLayout()
        login_layout.setAlignment(Qt.AlignCenter)
        
        self.login_link = QPushButton("Login")
        self.login_link.setObjectName("ColoredLink")
        self.login_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_link.clicked.connect(self._go_to_login)
        login_layout.addWidget(self.login_link)
        
        card_layout.addLayout(login_layout)
        
        main_layout.addWidget(card)
        
        self.display_name_input.setFocus()
    
    def _set_default_avatar(self):
        
        default_path = "Gui/assets/images/avatar.jpg"
        if os.path.exists(default_path):
            pixmap = load_circular_pixmap(default_path, size=100, border_width=0)
        else:
            from PySide6.QtGui import QPainter, QPainterPath
            pixmap = QPixmap(100, 100)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(Qt.GlobalColor.lightGray)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, 100, 100)
            painter.end()
        
        self.avatar_label.setPixmap(pixmap)
        self.avatar_label.setScaledContents(True)
    
    def _choose_avatar(self):
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Avatar Image",
            "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        
        if file_path:
            try:
                pixmap = load_circular_pixmap(file_path, size=100)
                self.avatar_label.setPixmap(pixmap)
                self.selected_avatar_path = file_path
                print(f"[Register] Selected avatar: {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load avatar: {str(e)}")
    
    def _register(self):
        
        username = self.username_input.text().strip()
        display_name = self.display_name_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        if not display_name:
            QMessageBox.warning(self, "Error", "Please enter your name")
            self.display_name_input.setFocus()
            return
        
        if not username:
            QMessageBox.warning(self, "Error", "Please enter your email")
            self.username_input.setFocus()
            return
        
        if not password:
            QMessageBox.warning(self, "Error", "Please enter a password")
            self.password_input.setFocus()
            return
        
        if password != confirm_password:
            QMessageBox.warning(self, "Error", "Passwords do not match")
            self.confirm_password_input.clear()
            self.confirm_password_input.setFocus()
            return
        
        success, message = self.user_manager.register(
            username=username,
            password=password,
            display_name=display_name,
            avatar_path=self.selected_avatar_path
        )
        
        if success:
            QMessageBox.information(
                self,
                "Success",
                f"Account created successfully!\nWelcome, {display_name}!"
            )
            self.registration_successful.emit(username, display_name)
            self.accept()
        else:
            QMessageBox.warning(self, "Registration Failed", message)
    
    def _go_to_login(self):
        
        self.reject()
    
    def _toggle_password_visibility(self, field):
        
        if field == 1:
            if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
                self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
                self.eye_icon1.setPixmap(QPixmap("Gui/assets/icons/eye_on.svg").scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
                self.eye_icon1.setPixmap(QPixmap("Gui/assets/icons/eye_off.svg").scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            if self.confirm_password_input.echoMode() == QLineEdit.EchoMode.Password:
                self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Normal)
                self.eye_icon2.setPixmap(QPixmap("Gui/assets/icons/eye_on.svg").scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
                self.eye_icon2.setPixmap(QPixmap("Gui/assets/icons/eye_off.svg").scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
