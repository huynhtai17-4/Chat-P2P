import socket
import sys
from PySide6.QtWidgets import QApplication

from Gui.view.stylesheet import STYLESHEET
from Gui.view.auth_stylesheet import AUTH_STYLESHEET
from Gui.view.login_window import LoginWindow
from Gui.view.register_window import RegisterWindow
from Gui.view.main_window import MainWindow
from app.user_manager import UserManager

class ChatApplication:

    def __init__(self):
        self.app = QApplication(sys.argv)

        combined_stylesheet = STYLESHEET + AUTH_STYLESHEET
        self.app.setStyleSheet(combined_stylesheet)

        self.user_manager = UserManager()

        self.current_user = None
        self.login_window = None
        self.register_window = None
        self.main_window = None
        self.navigate_to_register = False
    
    def run(self):
        self.show_login()
        return self.app.exec()
    
    def show_login(self):
        self.login_window = LoginWindow(self.user_manager)
        self.login_window.login_successful.connect(self.on_login_success)
        self.login_window.register_requested.connect(self._handle_register_requested)
        result = self.login_window.exec()
        self.login_window = None
        
        if self.navigate_to_register:
            self.navigate_to_register = False
            self.show_register()
            return
        
        if result == 0 and self.current_user is None:
            sys.exit(0)
    
    def show_register(self):
        self.register_window = RegisterWindow(self.user_manager)
        self.register_window.registration_successful.connect(self.on_register_success)
        result = self.register_window.exec()
        self.register_window = None
        if result == 0:
            self.show_login()
    
    def _handle_register_requested(self):
        self.navigate_to_register = True
        if self.login_window:
            self.login_window.reject()
    
    def on_login_success(self, user):
        self.current_user = user
        print(f"[App] User logged in: {user.display_name}")
        if self.login_window:
            self.login_window.close()
        self.show_main_window()
    
    def on_register_success(self, username, display_name):
        print(f"[App] User registered: {display_name}")
        if self.register_window:
            self.register_window.close()
        self.login_window = LoginWindow(self.user_manager)
        self.login_window.set_username(username)
        self.login_window.login_successful.connect(self.on_login_success)
        self.login_window.register_requested.connect(self._handle_register_requested)
        result = self.login_window.exec()
        if result == 0 and self.current_user is None:
            sys.exit(0)
    
    def show_main_window(self):
        if not self.current_user:
            return
        import json
        import os
        from app.user_manager import _normalize_username

        folder_name = _normalize_username(self.current_user.username)
        profile_path = os.path.join("data", folder_name, "profile.json")

        tcp_port = None
        if os.path.exists(profile_path):
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    profile = json.load(f)
                    saved_port = profile.get("tcp_port")
                    if saved_port and isinstance(saved_port, int) and saved_port > 0:
                        tcp_port = saved_port
                        print(f"[Main] Loaded TCP port {tcp_port} from profile.json")
            except Exception as e:
                print(f"[Main] Failed to load TCP port from profile: {e}")
        
        if tcp_port is None:
            tcp_port = self._allocate_tcp_port()
            print(f"[Main] Allocated new TCP port {tcp_port}")

        self.main_window = MainWindow(
            user_name=self.current_user.display_name,
            user_id=self.current_user.user_id,
            username=self.current_user.username,
            avatar_path=self.current_user.avatar_path,
            tcp_port=tcp_port
        )

        self.main_window.show()

    def _allocate_tcp_port(self, base: int = 55000, max_ports: int = 200) -> int:
        for offset in range(max_ports):
            port = base + offset
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                try:
                    sock.bind(("", port))
                    return port
                except OSError:
                    continue
        return 0

def main():
    
    app = ChatApplication()
    sys.exit(app.run())

if __name__ == "__main__":
    main()
