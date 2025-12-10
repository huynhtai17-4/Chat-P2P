"""
Audio capture and playback using PyAudio
"""
from __future__ import annotations

import logging
from typing import Callable, Optional
import threading

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
    print(f"[AudioStream] PyAudio imported successfully, version: {pyaudio.__version__ if hasattr(pyaudio, '__version__') else 'unknown'}")
except ImportError as e:
    PYAUDIO_AVAILABLE = False
    pyaudio = None
    print(f"[AudioStream] CRITICAL: Failed to import PyAudio: {e}")

log = logging.getLogger(__name__)
print(f"[AudioStream] Module loaded, PYAUDIO_AVAILABLE = {PYAUDIO_AVAILABLE}")

# Audio configuration
CHUNK_SIZE = 1024  # Frames per buffer
FORMAT = 8  # pyaudio.paInt16 (16-bit audio)
CHANNELS = 1  # Mono
RATE = 16000  # 16kHz sample rate (good quality, low bandwidth)


class AudioCapture:
    """Capture audio from microphone"""
    
    def __init__(self, on_audio: Callable[[bytes], None]):
        """
        Args:
            on_audio: Callback when audio chunk captured
        """
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio not available. Install with: pip install PyAudio")
        
        self.on_audio = on_audio
        self.p_audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self._running = False
    
    def start(self) -> bool:
        """Start capturing audio from microphone"""
        if self._running:
            return True
        
        try:
            self.stream = self.p_audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
                stream_callback=self._audio_callback
            )
            
            self.stream.start_stream()
            self._running = True
            log.info("[AudioCapture] Started capturing audio")
            return True
        except Exception as e:
            log.error(f"[AudioCapture] Failed to start: {e}")
            return False
    
    def stop(self):
        """Stop capturing"""
        self._running = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
        
        log.info("[AudioCapture] Stopped")
    
    def cleanup(self):
        """Release PyAudio resources"""
        self.stop()
        if self.p_audio:
            try:
                self.p_audio.terminate()
            except:
                pass
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback when audio chunk captured"""
        if status:
            log.warning(f"[AudioCapture] Status: {status}")
        
        if self.on_audio and in_data:
            try:
                self.on_audio(in_data)
            except Exception as e:
                log.error(f"[AudioCapture] Error in callback: {e}")
        
        return (None, pyaudio.paContinue)


class AudioPlayback:
    """Play audio to speaker"""
    
    def __init__(self):
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio not available. Install with: pip install PyAudio")
        
        self.p_audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self._running = False
        self._lock = threading.Lock()
        self._buffer = b''  # Audio buffer
    
    def start(self) -> bool:
        """Start audio playback stream"""
        if self._running:
            return True
        
        try:
            self.stream = self.p_audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK_SIZE,
                stream_callback=self._playback_callback
            )
            
            self.stream.start_stream()
            self._running = True
            log.info("[AudioPlayback] Started")
            return True
        except Exception as e:
            log.error(f"[AudioPlayback] Failed to start: {e}")
            return False
    
    def stop(self):
        """Stop playback"""
        self._running = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
        
        with self._lock:
            self._buffer = b''
        
        log.info("[AudioPlayback] Stopped")
    
    def cleanup(self):
        """Release PyAudio resources"""
        self.stop()
        if self.p_audio:
            try:
                self.p_audio.terminate()
            except:
                pass
    
    def play(self, audio_data: bytes):
        """Add audio data to playback buffer"""
        with self._lock:
            self._buffer += audio_data
    
    def _playback_callback(self, in_data, frame_count, time_info, status):
        """Callback to provide audio data for playback"""
        with self._lock:
            bytes_needed = frame_count * CHANNELS * 2  # 2 bytes per sample (16-bit)
            
            if len(self._buffer) >= bytes_needed:
                # Have enough data
                data = self._buffer[:bytes_needed]
                self._buffer = self._buffer[bytes_needed:]
            elif len(self._buffer) > 0:
                # Partial data, pad with silence
                data = self._buffer + b'\x00' * (bytes_needed - len(self._buffer))
                self._buffer = b''
            else:
                # No data, output silence
                data = b'\x00' * bytes_needed
        
        return (data, pyaudio.paContinue)

