from typing import TYPE_CHECKING, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtCore import QSize

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    np = None


class ActiveCallWindow(QWidget):
    call_ended = Signal()
    
    def __init__(self, peer_name: str, call_type: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Call with {peer_name}")
        self.peer_name = peer_name
        self.call_type = call_type
        
        if call_type == "video":
            self.setFixedSize(800, 600)
        else:
            self.setFixedSize(400, 300)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        if self.call_type == "video":
            video_container = QFrame()
            video_container.setObjectName("VideoContainer")
            video_layout = QVBoxLayout(video_container)
            video_layout.setContentsMargins(0, 0, 0, 0)
            
            self.remote_video_label = QLabel("Waiting for video...")
            self.remote_video_label.setObjectName("RemoteVideoLabel")
            self.remote_video_label.setAlignment(Qt.AlignCenter)
            self.remote_video_label.setMinimumSize(640, 480)
            video_layout.addWidget(self.remote_video_label)
            
            self.local_video_label = QLabel()
            self.local_video_label.setObjectName("LocalVideoLabel")
            self.local_video_label.setFixedSize(160, 120)
            self.local_video_label.move(620, 20)
            self.local_video_label.setParent(video_container)
            self.local_video_label.raise_()
            
            layout.addWidget(video_container, 1)
        else:
            info_widget = QWidget()
            info_layout = QVBoxLayout(info_widget)
            info_layout.setAlignment(Qt.AlignCenter)
            info_layout.setSpacing(20)
            
            avatar_label = QLabel()
            avatar_label.setAlignment(Qt.AlignCenter)
            from ..utils.avatar import load_circular_pixmap
            avatar_pixmap = load_circular_pixmap("Gui/assets/images/avatar1.jpg", size=100)
            avatar_label.setPixmap(avatar_pixmap)
            info_layout.addWidget(avatar_label, alignment=Qt.AlignCenter)
            
            name_label = QLabel(self.peer_name)
            name_label.setObjectName("CallAvatarLabel")
            name_label.setAlignment(Qt.AlignCenter)
            info_layout.addWidget(name_label)
            
            self.status_label = QLabel("00:00")
            self.status_label.setObjectName("CallStatusLabel")
            self.status_label.setAlignment(Qt.AlignCenter)
            info_layout.addWidget(self.status_label)
            
            layout.addWidget(info_widget, 1)
        
        controls_panel = self._create_controls_panel()
        layout.addWidget(controls_panel)
    
    def _create_controls_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("ControlsPanel")
        panel.setFixedHeight(80)
        
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(20)
        
        layout.addStretch()
        
        self.mute_btn = QPushButton("Mute")
        self.mute_btn.setObjectName("MuteButton")
        self.mute_btn.setFixedSize(80, 50)
        self.mute_btn.setCheckable(True)
        self.mute_btn.clicked.connect(self._on_mute_toggle)
        layout.addWidget(self.mute_btn)
        
        self.end_btn = QPushButton()
        self.end_btn.setObjectName("EndCallButton")
        self.end_btn.setIcon(QIcon("Gui/assets/icons/no-phone.svg"))
        self.end_btn.setIconSize(QSize(28, 28))
        self.end_btn.setFixedSize(60, 60)
        self.end_btn.clicked.connect(self._on_end_call)
        layout.addWidget(self.end_btn)
        
        if self.call_type == "video":
            self.camera_btn = QPushButton("Camera Off")
            self.camera_btn.setObjectName("CameraButton")
            self.camera_btn.setFixedSize(100, 50)
            self.camera_btn.setCheckable(True)
            self.camera_btn.clicked.connect(self._on_camera_toggle)
            layout.addWidget(self.camera_btn)
        
        layout.addStretch()
        
        return panel
    
    def update_remote_video_frame(self, frame_bytes: bytes):
        if not hasattr(self, 'remote_video_label') or not CV2_AVAILABLE:
            return
        
        try:
            nparr = np.frombuffer(frame_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return
            
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            h, w, ch = rgb_img.shape
            bytes_per_line = ch * w
            
            q_img = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            pixmap = QPixmap.fromImage(q_img)
            scaled_pixmap = pixmap.scaled(
                self.remote_video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.remote_video_label.setPixmap(scaled_pixmap)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[CallWindow] Failed to display frame: {e}")
    
    def update_local_video_frame(self, frame: Any):
        if not hasattr(self, 'local_video_label') or frame is None:
            return
        
        try:
            rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            h, w, ch = rgb_img.shape
            bytes_per_line = ch * w
            
            q_img = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            pixmap = QPixmap.fromImage(q_img)
            scaled_pixmap = pixmap.scaled(
                self.local_video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.local_video_label.setPixmap(scaled_pixmap)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[CallWindow] Failed to display local frame: {e}")
    
    def _on_mute_toggle(self, checked: bool):
        if checked:
            self.mute_btn.setText("Unmute")
        else:
            self.mute_btn.setText("Mute")
    
    def _on_camera_toggle(self, checked: bool):
        if checked:
            self.camera_btn.setText("Camera On")
        else:
            self.camera_btn.setText("Camera Off")
    
    def _on_end_call(self):
        self.call_ended.emit()
        self.close()

