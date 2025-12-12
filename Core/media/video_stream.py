from __future__ import annotations

import logging
from typing import Callable, Optional, TYPE_CHECKING
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

if TYPE_CHECKING:
    import cv2
    import numpy as np

log = logging.getLogger(__name__)

VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480
VIDEO_FPS = 15
JPEG_QUALITY = 60


class VideoCapture:
    def __init__(self, on_frame: Callable[[bytes], None]):
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV not available. Install with: pip install opencv-python")
        
        self.on_frame = on_frame
        self.cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self._paused = False
        self._latest_frame = None
    
    def start(self, camera_index: int = None) -> bool:
        if self._running:
            return True
        
        if camera_index is None:
            camera_index = self._find_available_camera()
            if camera_index is None:
                log.error("[VideoCapture] No available camera found")
                return False
        
        try:
            self.cap = cv2.VideoCapture(camera_index)
            
            if not self.cap.isOpened():
                log.error(f"[VideoCapture] Failed to open camera {camera_index}")
                if camera_index == 0:
                    log.info("[VideoCapture] Trying to find alternative camera...")
                    alt_index = self._find_available_camera()
                    if alt_index is not None and alt_index != 0:
                        self.cap = cv2.VideoCapture(alt_index)
                        if not self.cap.isOpened():
                            log.error(f"[VideoCapture] Alternative camera {alt_index} also failed")
                            return False
                        camera_index = alt_index
                        log.info(f"[VideoCapture] Using alternative camera {alt_index}")
                    else:
                        return False
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, VIDEO_FPS)
            
            ret, initial_frame = self.cap.read()
            if ret and initial_frame is not None:
                if initial_frame.shape[1] != VIDEO_WIDTH or initial_frame.shape[0] != VIDEO_HEIGHT:
                    initial_frame = cv2.resize(initial_frame, (VIDEO_WIDTH, VIDEO_HEIGHT))
                self._latest_frame = initial_frame.copy()
                log.info("[VideoCapture] Captured initial frame for preview")
            else:
                log.warning("[VideoCapture] Could not read initial frame, but camera opened")
            
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()
            self._running = True
            
            log.info(f"[VideoCapture] Started capturing from camera {camera_index}")
            return True
        except Exception as e:
            log.error(f"[VideoCapture] Failed to start: {e}", exc_info=True)
            return False
    
    def _find_available_camera(self) -> Optional[int]:
        for i in range(5):
            try:
                test_cap = cv2.VideoCapture(i)
                if test_cap.isOpened():
                    ret, frame = test_cap.read()
                    test_cap.release()
                    if ret and frame is not None:
                        log.info(f"[VideoCapture] Found available camera at index {i}")
                        return i
            except Exception as e:
                log.debug(f"[VideoCapture] Camera {i} test failed: {e}")
                continue
        return None
    
    def stop(self):
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
        frame_delay = 1.0 / VIDEO_FPS
        
        while not self._stop_event.is_set():
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    log.warning("[VideoCapture] Failed to read frame")
                    time.sleep(0.1)
                    continue
                
                if frame.shape[1] != VIDEO_WIDTH or frame.shape[0] != VIDEO_HEIGHT:
                    frame = cv2.resize(frame, (VIDEO_WIDTH, VIDEO_HEIGHT))
                
                self._latest_frame = frame.copy()
                
                if not self._paused:
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
                    _, buffer = cv2.imencode('.jpg', frame, encode_param)
                    frame_bytes = buffer.tobytes()
                    
                    if self.on_frame:
                        try:
                            self.on_frame(frame_bytes)
                        except Exception as e:
                            log.error(f"[VideoCapture] Error in callback: {e}")
                
                time.sleep(frame_delay)
                
            except Exception as e:
                if not self._stop_event.is_set():
                    log.error(f"[VideoCapture] Error in capture loop: {e}")
                break
    
    def set_paused(self, paused: bool):
        self._paused = paused
        log.info(f"[VideoCapture] Paused: {paused}")
    
    def get_frame(self):
        return self._latest_frame


class VideoDecoder:
    @staticmethod
    def decode_frame(frame_bytes: bytes) -> Optional[np.ndarray]:
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
        if frame is None:
            return b''
        
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return rgb_frame.tobytes()
        except Exception as e:
            log.warning(f"[VideoDecoder] Failed to convert frame: {e}")
            return b''

