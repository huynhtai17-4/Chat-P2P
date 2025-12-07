# auth_stylesheet.py - Modern stylesheet for login/register
AUTH_STYLESHEET = """
/* ===== MODERN LOGIN/REGISTER STYLE ===== */

/* White Card */
QWidget#LoginCard {
    background-color: white;
    border-radius: 20px;
}

/* Card Title */
QLabel#CardTitle {
    font-size: 32px;
    font-weight: bold;
    color: #2C3E50;
    font-family: 'Segoe UI', Arial, sans-serif;
    background-color: transparent;
}

/* Field Icons */
QLabel#FieldIcon {
    font-size: 24px;
    min-width: 30px;
    max-width: 30px;
    color: #999;
    background-color: transparent;
}

QLabel#EyeIcon {
    font-size: 20px;
    min-width: 25px;
    max-width: 25px;
    color: #999;
    background-color: transparent;
}

/* Underline Input Style */
QLineEdit#UnderlineInput {
    background-color: transparent;
    border: none;
    border-bottom: 2px solid #E0E0E0;
    padding: 10px 5px;
    font-size: 15px;
    color: #333;
    font-family: 'Segoe UI', Arial, sans-serif;
    background-color: transparent;
}

QLineEdit#UnderlineInput:focus {
    border-bottom: 2px solid #4A90E2;
    background-color: transparent;
}

QLineEdit#UnderlineInput::placeholder {
    color: #B0B0B0;
    background-color: transparent;
}

/* Modern Checkbox */
QCheckBox#ModernCheckbox {
    font-size: 13px;
    color: #555;
    font-family: 'Segoe UI', Arial, sans-serif;
    spacing: 8px;
    background-color: transparent;
}

QCheckBox#ModernCheckbox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #CCC;
    border-radius: 3px;
    background-color: white;
    background-color: transparent;
}

QCheckBox#ModernCheckbox::indicator:checked {
    background-color: #4A90E2;
    border: 2px solid #4A90E2;
}

/* Text Links */
QPushButton#TextLink {
    background-color: transparent;
    color: #4A90E2;
    border: none;
    font-size: 13px;
    font-family: 'Segoe UI', Arial, sans-serif;
    padding: 0px;
    text-align: right;
}

QPushButton#TextLink:hover {
    color: #3A7BC8;
    text-decoration: underline;
}

/* Modern Primary Button */
QPushButton#ModernPrimaryButton {
    background-color: #4A90E2;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: bold;
    font-family: 'Segoe UI', Arial, sans-serif;
}

QPushButton#ModernPrimaryButton:hover {
    background-color: #3A7BC8;
}

QPushButton#ModernPrimaryButton:pressed {
    background-color: #2A6BB0;
}

/* Bottom Label */
QLabel#BottomLabel {
    font-size: 13px;
    color: #666;
    font-family: 'Segoe UI', Arial, sans-serif;
}

/* Colored Link */
QPushButton#ColoredLink {
    background-color: transparent;
    color: #4A90E2;
    border: none;
    font-size: 13px;
    font-weight: 600;
    font-family: 'Segoe UI', Arial, sans-serif;
    padding: 0px;
}

QPushButton#ColoredLink:hover {
    color: #3A7BC8;
    text-decoration: underline;
}

/* Avatar Preview */
QLabel#AvatarPreview {
    border: 3px solid #4A90E2;
    border-radius: 50px;
    background-color: transparent;
}

/* Upload Avatar Button */
QPushButton#UploadAvatarButton {
    background-color: transparent;
    color: #4A90E2;
    border: 2px solid #4A90E2;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    font-family: 'Segoe UI', Arial, sans-serif;
}

QPushButton#UploadAvatarButton:hover {
    background-color: #E8F4FD;
}

QPushButton#UploadAvatarButton:pressed {
    background-color: #D0E8FA;
}

/* Message Boxes */
QMessageBox {
    background-color: white;
}

QMessageBox QLabel {
    font-size: 14px;
    color: #333;
    font-family: 'Segoe UI', Arial, sans-serif;
    background-color: transparent;
}

QMessageBox QPushButton {
    background-color: #4A90E2;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 600;
    min-width: 80px;
}

QMessageBox QPushButton:hover {
    background-color: #3A7BC8;
}
"""