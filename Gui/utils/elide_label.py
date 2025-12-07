from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QSize  # Đảm bảo import QSize
from PySide6.QtGui import QPainter, QFontMetrics, QColor

class ElideLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._elide_mode = Qt.ElideRight
        self._text = text
        self.setMinimumHeight(20)
        self.setWordWrap(False)

    def setText(self, text):
        self._text = text
        self.update()

    def setElideMode(self, mode):
        self._elide_mode = mode
        self.update()

    def minimumSizeHint(self):
        fm = self.fontMetrics()
        min_width = fm.horizontalAdvance("...")
        min_height = fm.height()
        return QSize(min_width, min_height)

    def sizeHint(self):
        return self.minimumSizeHint()

    def paintEvent(self, event):
        painter = QPainter(self)
        fm = QFontMetrics(self.font())
        elided = fm.elidedText(self._text, self._elide_mode, self.width())
        painter.drawText(self.rect(), Qt.AlignLeft | Qt.AlignVCenter, elided)
