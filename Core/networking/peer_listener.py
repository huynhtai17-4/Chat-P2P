from __future__ import annotations

import json
import logging
import socket
import threading
from typing import Callable, Optional

from Core.models.message import Message
from Core.storage.data_manager import DataManager
from Core.utils import config

log = logging.getLogger(__name__)

class PeerListener:

    def __init__(self, peer_id: str, data_manager: DataManager, on_message: Optional[Callable[[Message], None]] = None):
        self.peer_id = peer_id
        self.data_manager = data_manager
        self.on_message = on_message

        self._server_socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self, host: str = "0.0.0.0", port: int = config.TCP_BASE_PORT) -> int:
        if self._thread and self._thread.is_alive():
            actual_port = self._server_socket.getsockname()[1]
            return actual_port

        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            try:
                self._server_socket.bind((host, port))
            except OSError as e:
                log.error("Failed to bind TCP listener socket on %s:%s -> %s", host, port, e)
                self._server_socket.close()
                self._server_socket = None
                raise RuntimeError(f"Failed to bind PeerListener socket on {host}:{port}. Port might be in use or permissions issue. Error: {e}") from e
            
            self._server_socket.listen(5)
            actual_port = self._server_socket.getsockname()[1]
            
            self._thread = threading.Thread(target=self._accept_loop, daemon=True, name="PeerListener")
            self._stop_event.clear()
            self._thread.start()
            
            log.info("[TCP] Listener started on %s (host=%s, requested=%s)", actual_port, host, port)
            return actual_port
        except OSError as e:
            log.error("Failed to start TCP listener to %s:%s: %s", host, port, e, exc_info=True)
            if self._server_socket:
                try:
                    self._server_socket.close()
                except:
                    pass
                self._server_socket = None
            raise RuntimeError(f"Failed to start TCP listener on port {port}: {e}") from e
        except Exception as e:
            log.error("Unexpected error starting TCP listener: %s", e, exc_info=True)
            if self._server_socket:
                try:
                    self._server_socket.close()
                except:
                    pass
                self._server_socket = None
            raise

    def stop(self):
        self._stop_event.set()
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass
        self._server_socket = None

    def _accept_loop(self):
        while not self._stop_event.is_set():
            try:
                if not self._server_socket:
                    break
                client_sock, addr = self._server_socket.accept()
                log.debug("Accepted connection from %s:%s", addr[0] if addr else "unknown", addr[1] if addr and len(addr) > 1 else "unknown")
            except OSError as e:
                if not self._stop_event.is_set():
                    log.debug("Accept loop stopped: %s", e)
                break
            except Exception as e:
                log.error("Unexpected error in accept loop: %s", e, exc_info=True)
                continue
            
            try:
                threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, addr),
                    daemon=True,
                    name=f"PeerListenerClient-{addr[0] if addr else 'unknown'}"
                ).start()
            except Exception as e:
                log.error("Failed to start client handler thread: %s", e, exc_info=True)
                try:
                    client_sock.close()
                except:
                    pass

    def _handle_client(self, client_sock: socket.socket, addr):
        buffer = ""
        sender_ip = addr[0] if addr and len(addr) > 0 else "unknown"
        sender_port = addr[1] if addr and len(addr) > 1 else 0
        
        try:
            with client_sock:
                client_sock.settimeout(5.0)
                log.debug("Handling client connection from %s:%s", sender_ip, sender_port)
                
                try:
                    while True:
                        try:
                            data = client_sock.recv(config.BUFFER_SIZE)
                            if not data:
                                log.debug("Client %s:%s disconnected (no data)", sender_ip, sender_port)
                                break
                            
                            try:
                                decoded = data.decode("utf-8")
                            except UnicodeDecodeError as e:
                                log.warning("Invalid UTF-8 data from %s:%s: %s", sender_ip, sender_port, e)
                                continue
                            
                            buffer += decoded
                            
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                line = line.strip()
                                if not line:
                                    continue
                                
                                try:
                                    self._process_line(line, addr)
                                except Exception as e:
                                    log.error("Error processing line from %s:%s: %s (line: %s)", sender_ip, sender_port, e, line[:100], exc_info=True)
                                    continue
                                    
                        except socket.timeout:
                            continue
                        except ConnectionError as e:
                            log.debug("Connection error from %s:%s: %s", sender_ip, sender_port, e)
                            break
                        except OSError as e:
                            log.debug("OS error from %s:%s: %s", sender_ip, sender_port, e)
                            break
                            
                except Exception as e:
                    log.error("Unexpected error handling client %s:%s: %s", sender_ip, sender_port, e, exc_info=True)
                    
        except Exception as e:
            log.error("Critical error in _handle_client for %s:%s: %s", sender_ip, sender_port, e, exc_info=True)
        
        log.debug("Client handler finished for %s:%s", sender_ip, sender_port)

    def _process_line(self, payload: str, addr):
        sender_ip = addr[0] if addr and len(addr) > 0 else "unknown"
        sender_port = addr[1] if addr and len(addr) > 1 else 0
        
        if not payload or not payload.strip():
            log.debug("Empty payload from %s:%s", sender_ip, sender_port)
            return
        
        try:
            message = Message.from_json(payload)
        except json.JSONDecodeError as e:
            log.warning("Invalid JSON from %s:%s: %s (payload: %s)", sender_ip, sender_port, e, payload[:200])
            return
        except (TypeError, ValueError, KeyError) as e:
            log.warning("Invalid message format from %s:%s: %s (payload: %s)", sender_ip, sender_port, e, payload[:200])
            return
        except Exception as e:
            log.error("Unexpected error parsing message from %s:%s: %s (payload: %s)", sender_ip, sender_port, e, payload[:200], exc_info=True)
            return

        sender_ip = addr[0] if addr and len(addr) > 0 else ""
        sender_port = addr[1] if addr and len(addr) > 1 else 0

        if self.on_message:
            try:
                self.on_message(message, sender_ip, sender_port)
                log.debug("Processed message from %s:%s (type: %s)", sender_ip, sender_port, message.msg_type)
            except Exception as e:
                log.error("Error in on_message callback for %s:%s: %s", sender_ip, sender_port, e, exc_info=True)
