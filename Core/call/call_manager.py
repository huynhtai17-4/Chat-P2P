from __future__ import annotations

import logging
from typing import Optional, Callable
from enum import Enum

from Core.networking.udp_stream import UDPSender, UDPReceiver
from Core.media.audio_stream import AudioCapture, AudioPlayback
from Core.media.video_stream import VideoCapture, VideoDecoder

log = logging.getLogger(__name__)


class CallState(Enum):
    IDLE = "idle"
    OUTGOING = "outgoing"
    INCOMING = "incoming"
    ACTIVE = "active"
    ENDING = "ending"


class CallType(Enum):
    VOICE = "voice"
    VIDEO = "video"


class CallManager:
    def __init__(self):
        self.state = CallState.IDLE
        self.call_type: Optional[CallType] = None
        self.peer_id: Optional[str] = None
        self.peer_name: Optional[str] = None
        self.peer_ip: Optional[str] = None
        self.peer_tcp_port: Optional[int] = None

        self.local_audio_port = 56000
        self.local_video_port = 57000
        self.peer_audio_port: Optional[int] = None
        self.peer_video_port: Optional[int] = None

        self.audio_capture: Optional[AudioCapture] = None
        self.audio_playback: Optional[AudioPlayback] = None
        self.video_capture: Optional[VideoCapture] = None

        self.audio_sender: Optional[UDPSender] = None
        self.video_sender: Optional[UDPSender] = None
        self.audio_receiver: Optional[UDPReceiver] = None
        self.video_receiver: Optional[UDPReceiver] = None

        self.on_call_state_changed: Optional[Callable[[CallState], None]] = None
        self.on_remote_video_frame: Optional[Callable[[bytes], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        self._is_muted = False
        self._is_camera_off = False
    
    def start_outgoing_call(self, peer_id: str, peer_name: str, peer_ip: str, 
                           call_type: CallType) -> tuple[bool, int, int]:
        if self.state != CallState.IDLE:
            log.warning("[CallManager] Cannot start call - already in call")
            return False, 0, 0
        
        self.state = CallState.OUTGOING
        self.call_type = call_type
        self.peer_id = peer_id
        self.peer_name = peer_name
        self.peer_ip = peer_ip

        log.info(f"[CallManager] Starting {call_type.value} call to {peer_name}")

        if not self._start_receivers(call_type):
            self._cleanup()
            return False, 0, 0

        video_port = self.local_video_port if call_type == CallType.VIDEO else 0

        self._notify_state_changed()
        return True, self.local_audio_port, video_port
    
    def prepare_incoming_call(self, peer_id: str, peer_name: str, peer_ip: str,
                             call_type: CallType, peer_audio_port: int, 
                             peer_video_port: int = 0) -> bool:
        if self.state != CallState.IDLE:
            log.warning("[CallManager] Cannot prepare incoming call - already in call")
            return False

        self.call_type = call_type
        self.peer_id = peer_id
        self.peer_name = peer_name
        self.peer_ip = peer_ip
        self.peer_audio_port = peer_audio_port
        self.peer_video_port = peer_video_port

        log.info(f"[CallManager] Prepared incoming {call_type.value} call from {peer_name}")
        return True
    
    def accept_incoming_call(self) -> tuple[bool, int, int]:
        if self.state != CallState.IDLE:
            log.warning("[CallManager] Cannot accept call - already in call")
            return False, 0, 0
        
        if not self.peer_id or not self.call_type:
            log.warning("[CallManager] No incoming call to accept")
            return False, 0, 0
        
        self.state = CallState.INCOMING
        log.info(f"[CallManager] Accepting {self.call_type.value} call from {self.peer_name}")
        
        if not self._start_receivers(self.call_type):
            self._cleanup()
            return False, 0, 0
        
        video_port = self.local_video_port if self.call_type == CallType.VIDEO else 0
        
        return True, self.local_audio_port, video_port
    
    def start_media_streams(self, peer_audio_port: int, peer_video_port: int = 0) -> bool:
        self.peer_audio_port = peer_audio_port
        self.peer_video_port = peer_video_port

        log.info(f"[CallManager] Starting media streams to {self.peer_ip}:{peer_audio_port}")

        self.audio_sender = UDPSender()
        self.audio_sender.set_target(self.peer_ip, peer_audio_port)

        if self.call_type == CallType.VIDEO and peer_video_port > 0:
            self.video_sender = UDPSender()
            self.video_sender.set_target(self.peer_ip, peer_video_port)

        try:
            self.audio_capture = AudioCapture(on_audio=self._on_audio_captured)
            if not self.audio_capture.start():
                raise RuntimeError("Failed to start audio capture")
            
            self.audio_playback = AudioPlayback()
            if not self.audio_playback.start():
                raise RuntimeError("Failed to start audio playback")
        except Exception as e:
            log.error(f"[CallManager] Audio initialization failed: {e}")
            if self.on_error:
                self.on_error(f"Microphone/speaker error: {e}")
            self._cleanup()
            return False

        if self.call_type == CallType.VIDEO:
            try:
                self.video_capture = VideoCapture(on_frame=self._on_video_captured)
                if not self.video_capture.start():
                    error_msg = "Failed to start camera. Please check:\n1. Camera permissions\n2. Camera is not used by another app\n3. Camera drivers are installed"
                    log.error(f"[CallManager] Video initialization failed: {error_msg}")
                    if self.on_error:
                        self.on_error(error_msg)
                    self.video_capture = None
            except Exception as e:
                error_msg = f"Camera error: {e}\n\nPlease check:\n1. Camera permissions in Windows Settings\n2. Camera is not used by another app\n3. Camera drivers are installed"
                log.error(f"[CallManager] Video initialization failed: {e}", exc_info=True)
                if self.on_error:
                    self.on_error(error_msg)
                self.video_capture = None
        
        self.state = CallState.ACTIVE
        self._notify_state_changed()
        
        log.info("[CallManager] Media streams started successfully")
        return True
    
    def end_call(self):
        if self.state == CallState.IDLE:
            return
        
        log.info("[CallManager] Ending call")
        self.state = CallState.ENDING
        self._notify_state_changed()
        
        self._cleanup()
        
        self.state = CallState.IDLE
        self.call_type = None
        self.peer_id = None
        self.peer_name = None
        self.peer_ip = None
        self.peer_audio_port = None
        self.peer_video_port = None
        
        self._notify_state_changed()
    
    def _start_receivers(self, call_type: CallType) -> bool:
        try:
            self.audio_receiver = UDPReceiver(
                port=self.local_audio_port,
                on_data=self._on_audio_received
            )
            if not self.audio_receiver.start():
                raise RuntimeError(f"Failed to bind audio port {self.local_audio_port}")

            if call_type == CallType.VIDEO:
                self.video_receiver = UDPReceiver(
                    port=self.local_video_port,
                    on_data=self._on_video_received
                )
                if not self.video_receiver.start():
                    raise RuntimeError(f"Failed to bind video port {self.local_video_port}")
            
            return True
        except Exception as e:
            log.error(f"[CallManager] Failed to start receivers: {e}")
            if self.on_error:
                self.on_error(f"Port binding error: {e}")
            return False
    
    def _on_audio_captured(self, audio_data: bytes):
        if self.audio_sender and self.state == CallState.ACTIVE and not self._is_muted:
            if audio_data and len(audio_data) > 0:
                self.audio_sender.send(audio_data)
            else:
                log.warning("[CallManager] Captured empty audio data")
    
    def _on_video_captured(self, frame_bytes: bytes):
        if self.video_sender and self.state == CallState.ACTIVE:
            self.video_sender.send(frame_bytes)
    
    def _on_audio_received(self, audio_data: bytes):
        if self.audio_playback and self.state == CallState.ACTIVE:
            if audio_data and len(audio_data) > 0:
                self.audio_playback.play(audio_data)
            else:
                log.warning("[CallManager] Received empty audio data")
        else:
            log.debug(f"[CallManager] Ignoring audio - playback={self.audio_playback is not None}, state={self.state}")
    
    def _on_video_received(self, frame_bytes: bytes):
        if self.on_remote_video_frame and self.state == CallState.ACTIVE:
            self.on_remote_video_frame(frame_bytes)
    
    def _cleanup(self):
        if self.audio_capture:
            self.audio_capture.stop()
            self.audio_capture.cleanup()
            self.audio_capture = None
        
        if self.audio_playback:
            self.audio_playback.stop()
            self.audio_playback.cleanup()
            self.audio_playback = None
        
        if self.video_capture:
            self.video_capture.stop()
            self.video_capture = None

        if self.audio_receiver:
            self.audio_receiver.stop()
            self.audio_receiver = None

        if self.video_receiver:
            self.video_receiver.stop()
            self.video_receiver = None

        if self.audio_sender:
            self.audio_sender.close()
            self.audio_sender = None

        if self.video_sender:
            self.video_sender.close()
            self.video_sender = None
    
    def _notify_state_changed(self):
        if self.on_call_state_changed:
            try:
                self.on_call_state_changed(self.state)
            except Exception as e:
                log.error(f"[CallManager] Error in state callback: {e}")
    
    def is_in_call(self) -> bool:
        return self.state != CallState.IDLE
    
    def get_state(self) -> CallState:
        return self.state
    
    def toggle_mute(self, is_muted: bool):
        self._is_muted = is_muted
        if self.audio_capture:
            self.audio_capture.set_muted(is_muted)
        log.info(f"[CallManager] Audio muted: {is_muted}")
    
    def toggle_camera(self, is_off: bool):
        self._is_camera_off = is_off
        if self.video_capture:
            self.video_capture.set_paused(is_off)
        log.info(f"[CallManager] Camera off: {is_off}")
    
    def get_local_frame(self):
        if self.video_capture and not self._is_camera_off:
            return self.video_capture.get_frame()
        return None

