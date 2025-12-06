#!/usr/bin/env python3
"""
Quick test script for Login/Register windows
"""
import sys
from PySide6.QtWidgets import QApplication
from Gui.view.auth_stylesheet import AUTH_STYLESHEET
from Gui.view.login_window import LoginWindow
from Gui.view.register_window import RegisterWindow
from app.user_manager import UserManager

def test_login():
    """Test login window"""
    app = QApplication(sys.argv)
    app.setStyleSheet(AUTH_STYLESHEET)
    
    user_manager = UserManager()
    
    login_window = LoginWindow(user_manager)
    
    print("✅ Login window created successfully")
    print("Opening login window...")
    
    result = login_window.exec()
    
    if result:
        print("✅ Login window accepted (user clicked Login/OK)")
    else:
        print("⚠️  Login window rejected (user clicked Cancel/X)")
    
    return 0

def test_register():
    """Test register window"""
    app = QApplication(sys.argv)
    app.setStyleSheet(AUTH_STYLESHEET)
    
    user_manager = UserManager()
    
    register_window = RegisterWindow(user_manager)
    
    print("✅ Register window created successfully")
    print("Opening register window...")
    
    result = register_window.exec()
    
    if result:
        print("✅ Register window accepted (user registered)")
    else:
        print("⚠️  Register window rejected (user cancelled)")
    
    return 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Login/Register windows')
    parser.add_argument('window', choices=['login', 'register'], 
                       help='Which window to test')
    
    args = parser.parse_args()
    
    if args.window == 'login':
        sys.exit(test_login())
    else:
        sys.exit(test_register())

