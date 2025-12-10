import os
import base64
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap


class MessageBubble(QLabel):
    def __init__(self, text, is_sender=True, time_str=None, file_name=None, file_data=None, msg_type="text", local_file_path=None):
        self.file_name = file_name
        self.file_data = file_data
        self.is_sender = is_sender
        self.msg_type = msg_type
        self.local_file_path = local_file_path

        container = None
        layout = None

        has_file_payload = (file_name is not None) and (file_data is not None or local_file_path is not None)

        if msg_type in ("image", "file") and has_file_payload:
            super().__init__()
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            
            file_widget = self._create_file_widget(file_name, file_data, msg_type)
            layout.addWidget(file_widget)

            if text and msg_type != "image":
                label = QLabel(text)
                label.setWordWrap(True)
                label.setObjectName("FileTextLabel")
                layout.addWidget(label)

            if time_str:
                time_label = QLabel(time_str)
                time_label.setObjectName("MessageTimestamp")
                time_label.setAlignment(Qt.AlignRight if is_sender else Qt.AlignLeft)
                layout.addWidget(time_label)

            self._container = container

        elif time_str or text:
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)

            super().__init__(text if text else "")
            self.setWordWrap(True)
            layout.addWidget(self)

            if time_str:
                time_label = QLabel(time_str)
                time_label.setObjectName("MessageTimestamp")
                time_label.setAlignment(Qt.AlignRight if is_sender else Qt.AlignLeft)
            layout.addWidget(time_label)
            
            self._container = container
        else:
            super().__init__(text if text else "")
            self.setWordWrap(True)
            self._container = None
        
        max_width = 420
        if self._container:
            self._container.setMaximumWidth(max_width)
        else:
            self.setMaximumWidth(max_width)
        
        if is_sender:
            self.setObjectName("MessageBubbleSelf")
        else:
            self.setObjectName("MessageBubbleOther")

        self.setProperty("class", "MessageBubble")
    
    def _create_file_widget(self, file_name: str, file_data_base64: str | None, msg_type: str = "file") -> QWidget:
        file_widget = QWidget()
        layout = QVBoxLayout(file_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        if msg_type == "image":
            try:
                pixmap = QPixmap()
                if file_data_base64:
                    image_data = base64.b64decode(file_data_base64)
                    pixmap.loadFromData(image_data)
                elif self.local_file_path and os.path.exists(self.local_file_path):
                    pixmap.load(self.local_file_path)
                
                max_width = 300
                max_height = 300
                
                if pixmap.width() > max_width or pixmap.height() > max_height:
                    pixmap = pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                image_label = QLabel()
                image_label.setPixmap(pixmap)
                image_label.setAlignment(Qt.AlignCenter)
                image_label.setScaledContents(False)
                image_label.setObjectName("MessageImageLabel")
                image_label.setFixedSize(pixmap.size())
                layout.addWidget(image_label)
            except Exception as e:
                file_label = QLabel("Failed to load image")
                file_label.setObjectName("FileErrorLabel")
                layout.addWidget(file_label)
        else:
            file_container = QWidget()
            file_container.setObjectName("FileContainer")
            file_layout = QVBoxLayout(file_container)
            file_layout.setContentsMargins(12, 10, 12, 10)
            file_layout.setSpacing(6)
            
            file_info_layout = QHBoxLayout()
            file_info_layout.setContentsMargins(0, 0, 0, 0)
            file_info_layout.setSpacing(10)
            
            file_icon_label = QLabel("📄")
            file_icon_label.setObjectName("FileIconLabel")
            file_info_layout.addWidget(file_icon_label)
            
            file_info_widget = QWidget()
            file_info_layout_inner = QVBoxLayout(file_info_widget)
            file_info_layout_inner.setContentsMargins(0, 0, 0, 0)
            file_info_layout_inner.setSpacing(2)
            
            name_label = QLabel(file_name)
            name_label.setObjectName("FileNameLabel")
            name_label.setWordWrap(True)
            file_info_layout_inner.addWidget(name_label)
            
            file_ext = os.path.splitext(file_name)[1].upper()
            if not file_ext:
                file_ext = "FILE"
            else:
                file_ext = file_ext[1:]
            
            type_label = QLabel(f"{file_ext} File")
            type_label.setObjectName("FileTypeLabel")
            file_info_layout_inner.addWidget(type_label)
            
            file_info_layout.addWidget(file_info_widget, 1)
            file_layout.addLayout(file_info_layout)
            
            file_container.setCursor(Qt.PointingHandCursor)
            file_container.mousePressEvent = lambda event: self._open_file(file_name, file_data_base64)
            
            download_btn = QPushButton("Download")
            download_btn.setObjectName("FileDownloadButton")
            download_btn.setFixedHeight(32)
            download_btn.clicked.connect(lambda: self._download_file(file_name, file_data_base64))
            file_layout.addWidget(download_btn)
            
            layout.addWidget(file_container)
        
        return file_widget
    
    def _open_file(self, file_name: str, file_data_base64: str):
        try:
            import tempfile
            import subprocess
            import platform
            target_path = None
            
            if self.local_file_path and os.path.exists(self.local_file_path):
                target_path = self.local_file_path
            else:
                temp_dir = tempfile.gettempdir()
                target_path = os.path.join(temp_dir, file_name)
                file_data = base64.b64decode(file_data_base64)
                with open(target_path, 'wb') as f:
                    f.write(file_data)
            
            if platform.system() == 'Darwin':
                subprocess.call(('open', target_path))
            elif platform.system() == 'Windows':
                os.startfile(target_path)
            else:
                subprocess.call(('xdg-open', target_path))
                
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Open Error", f"Error opening file: {e}")
    
    def _download_file(self, file_name: str, file_data_base64: str):
        try:
            from PySide6.QtWidgets import QFileDialog
            from PySide6.QtCore import QStandardPaths
            
            downloads_path = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
            if not downloads_path:
                downloads_path = os.path.expanduser("~")
            
            file_path, _ = QFileDialog.getSaveFileName(
                None,
                "Save File",
                os.path.join(downloads_path, file_name),
                "All Files (*)"
            )
            
            if file_path:
                if self.local_file_path and os.path.exists(self.local_file_path):
                    import shutil
                    shutil.copyfile(self.local_file_path, file_path)
                else:
                    file_data = base64.b64decode(file_data_base64)
                    with open(file_path, 'wb') as f:
                        f.write(file_data)
                
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(None, "Download Complete", f"File saved to:\n{file_path}")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Download Error", f"Error downloading file: {e}")
    
    def get_widget(self):
        return self._container if self._container else self
