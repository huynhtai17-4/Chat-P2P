from __future__ import annotations

import socket
import threading
import logging
from typing import Callable, Optional
import struct

log = logging.getLogger(__name__)

class UDPSender:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.target_ip: Optional[str] = None
        self.target_port: Optional[int] = None
        
    def set_target(self, ip: str, port: int):
        self.target_ip = ip
        self.target_port = port
        log.info(f"[UDPSender] Target set to {ip}:{port}")
    
    def send(self, data: bytes) -> bool:
        if not self.target_ip or not self.target_port:
            return False
        
        try:
            if not hasattr(self, '_seq_num'):
                self._seq_num = 0
            
            packet = struct.pack('!I', self._seq_num) + data
            self._seq_num = (self._seq_num + 1) % (2**32)
            
            self.sock.sendto(packet, (self.target_ip, self.target_port))
            return True
        except Exception as e:
            log.warning(f"[UDPSender] Failed to send: {e}")
            return False
    
    def close(self):
        try:
            self.sock.close()
        except:
            pass


class UDPReceiver:
    def __init__(self, port: int, on_data: Callable[[bytes], None]):
        self.port = port
        self.on_data = on_data
        self.sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
    
    def start(self) -> bool:
        if self._running:
            return True
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("0.0.0.0", self.port))
            self.sock.settimeout(1.0)
            
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._thread.start()
            self._running = True
            
            log.info(f"[UDPReceiver] Started on port {self.port}")
            return True
        except Exception as e:
            log.error(f"[UDPReceiver] Failed to start on port {self.port}: {e}")
            return False
    
    def stop(self):
        self._stop_event.set()
        self._running = False
        
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        
        log.info(f"[UDPReceiver] Stopped on port {self.port}")
    
    def _receive_loop(self):
        buffer_size = 65536
        
        while not self._stop_event.is_set():
            try:
                data, addr = self.sock.recvfrom(buffer_size)
                
                if len(data) < 4:
                    continue
                
                seq_num = struct.unpack('!I', data[:4])[0]
                payload = data[4:]
                
                if self.on_data:
                    try:
                        self.on_data(payload)
                    except Exception as e:
                        log.error(f"[UDPReceiver] Error in callback: {e}")
                        
            except socket.timeout:
                continue
            except Exception as e:
                if not self._stop_event.is_set():
                    log.warning(f"[UDPReceiver] Error receiving: {e}")
                break

