from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QPen
from PySide6.QtCore import Qt, QRectF

def load_circular_pixmap(image_path, size=40, border_width=0, border_color="#dddddd"):
    pixmap = QPixmap(image_path)
    if pixmap.isNull():
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor("#888888"))
    circular_pixmap = QPixmap(size, size)
    circular_pixmap.fill(Qt.transparent)
    
    painter = QPainter(circular_pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    if border_width > 0:
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(border_color))
        painter.drawEllipse(0, 0, size, size)
    image_inset = border_width
    image_size = size - (border_width * 2)
    
    path = QPainterPath()
    path.addEllipse(image_inset, image_inset, image_size, image_size)
    painter.setClipPath(path)

    scaled_pixmap = pixmap.scaled(
        size, size,
        Qt.KeepAspectRatioByExpanding,
        Qt.SmoothTransformation
    )
    
    scaled_width = scaled_pixmap.width()
    scaled_height = scaled_pixmap.height()
    
    x_offset = (size - scaled_width) / 2
    y_offset = (size - scaled_height) / 2
    
    painter.drawPixmap(x_offset, y_offset, scaled_pixmap)
    
    painter.end()
    return circular_pixmap

class Avatar(QLabel):
    
    def __init__(self, image_path, size=40, border_width=0, border_color="#dddddd", parent=None):
        super().__init__(parent)
        pixmap = load_circular_pixmap(image_path, size, border_width, border_color)
        self.setPixmap(pixmap)
        self.setFixedSize(size, size)
