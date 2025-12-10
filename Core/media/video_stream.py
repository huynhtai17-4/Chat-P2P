"""
Video capture and processing using OpenCV
"""
from __future__ import annotations

import logging
from typing import Callable, Optional
import threading
import time

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

log = logging.getLogger(__name__)

# Video configuration
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480
VIDEO_FPS = 15  # 15 FPS for lower bandwidth
JPEG_QUALITY = 60  # 0-100, lower = smaller size


class VideoCapture:
    """Capture video from webcam"""
    
    def __init__(self, on_frame: Callable[[bytes], None]):
        """
        Args:
            on_frame: Callback when frame captured (gets JPEG bytes)
        """
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV not available. Install with: pip install opencv-python")
        
        self.on_frame = on_frame
        self.cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
    
    def start(self, camera_index: int = 0) -> bool:
        """Start capturing video from webcam"""
        if self._running:
            return True
        
        try:
            self.cap = cv2.VideoCapture(camera_index)
            
            if not self.cap.isOpened():
                log.error("[VideoCapture] Failed to open camera")
                return False
            
            # Set camera resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, VIDEO_FPS)
            
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()
            self._running = True
            
            log.info(f"[VideoCapture] Started capturing from camera {camera_index}")
            return True
        except Exception as e:
            log.error(f"[VideoCapture] Failed to start: {e}")
            return False
    
    def stop(self):
        """Stop capturing"""
        self._stop_event.set()
        self._running = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None
        
        log.info("[VideoCapture] Stopped")
    
    def _capture_loop(self):
        """Main loop to capture frames"""
        frame_delay = 1.0 / VIDEO_FPS
        
        while not self._stop_event.is_set():
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    log.warning("[VideoCapture] Failed to read frame")
                    time.sleep(0.1)
                    continue
                
                # Resize if needed
                if frame.shape[1] != VIDEO_WIDTH or frame.shape[0] != VIDEO_HEIGHT:
                    frame = cv2.resize(frame, (VIDEO_WIDTH, VIDEO_HEIGHT))
                
                # Encode to JPEG for transmission
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                frame_bytes = buffer.tobytes()
                
                # Call callback
                if self.on_frame:
                    try:
                        self.on_frame(frame_bytes)
                    except Exception as e:
                        log.error(f"[VideoCapture] Error in callback: {e}")
                
                # Maintain FPS
                time.sleep(frame_delay)
                
            except Exception as e:
                if not self._stop_event.is_set():
                    log.error(f"[VideoCapture] Error in capture loop: {e}")
                break


class VideoDecoder:
    """Decode and process received video frames"""
    
    @staticmethod
    def decode_frame(frame_bytes: bytes) -> Optional[np.ndarray]:
        """Decode JPEG bytes to numpy array (OpenCV image)"""
        if not CV2_AVAILABLE:
            return None
        
        try:
            nparr = np.frombuffer(frame_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            log.warning(f"[VideoDecoder] Failed to decode frame: {e}")
            return None
    
    @staticmethod
    def frame_to_rgb_bytes(frame: np.ndarray) -> bytes:
        """Convert OpenCV frame (BGR) to RGB bytes for Qt display"""
        if frame is None:
            return b''
        
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return rgb_frame.tobytes()
        except Exception as e:
            log.warning(f"[VideoDecoder] Failed to convert frame: {e}")
            return b''

