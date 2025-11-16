# main_window.py
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QSplitter
from PySide6.QtCore import Qt

# Import 3 cột chính
from .chat_list import ChatList
from .chat_area import ChatArea
from .notifications_panel import NotificationsPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat ONN (Python/PySide6)")
        self.setGeometry(100, 100, 1500, 900) # Kích thước cửa sổ
        self.setMinimumSize(800, 600)
        # Widget trung tâm để chứa layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Layout chính (theo chiều ngang)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10) # Khoảng cách với viền
        main_layout.setSpacing(0) # Không có khoảng cách giữa các cột

        # --- Dùng QSplitter để cho phép kéo, thay đổi kích thước ---
        
        # 1. Khởi tạo 3 component cột
        self.left_sidebar = ChatList()
        self.center_panel = ChatArea()
        self.right_sidebar = NotificationsPanel()
        
        # 2. Bộ chia bên phải (Giữa Cột Giữa và Cột Phải)
        splitter_right = QSplitter(Qt.Horizontal)
        splitter_right.addWidget(self.center_panel)
        splitter_right.addWidget(self.right_sidebar)
        splitter_right.setStretchFactor(0, 3) # Cột giữa co giãn gấp 3
        splitter_right.setStretchFactor(1, 1)

        # 3. Bộ chia chính (Giữa Cột Trái và [Cụm Phải])
        splitter_main = QSplitter(Qt.Horizontal)
        splitter_main.addWidget(self.left_sidebar)
        splitter_main.addWidget(splitter_right)
        splitter_main.setStretchFactor(0, 1) 
        splitter_main.setStretchFactor(1, 4) # Cụm phải co giãn gấp 4
        
        main_layout.addWidget(splitter_main)
        splitter_main.setSizes([325, 1000])