import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Signal

class TestWidget(QWidget):
    button_clicked_signal = Signal(str, str)
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        btn = QPushButton("Test Add Button")
        btn.clicked.connect(lambda checked: self.button_clicked_signal.emit("test_id", "test_name"))
        layout.addWidget(btn)
        
        self.button_clicked_signal.connect(self.on_button_clicked)
    
    def on_button_clicked(self, peer_id, peer_name):
        print(f"✓ Button clicked! peer_id={peer_id}, peer_name={peer_name}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = TestWidget()
    widget.show()
    sys.exit(app.exec())
