# main.py
import sys
from PySide6.QtWidgets import QApplication

# Import file stylesheet và cửa sổ chính
from Gui.view.stylesheet import STYLESHEET
from Gui.view.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Áp dụng QSS cho TOÀN BỘ ứng dụng
    app.setStyleSheet(STYLESHEET)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())