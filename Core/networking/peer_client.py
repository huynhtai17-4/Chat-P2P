from __future__ import annotations

import logging
import socket

from Core.models.message import Message
from Core.utils import config

log = logging.getLogger(__name__)

class PeerClient:

    def send(self, peer_ip: str, peer_port: int, message: Message) -> bool:
        print(f"[PeerClient] Attempting to send {message.msg_type} to {peer_ip}:{peer_port}")
        payload = message.to_json() + "\n"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(config.TCP_CONNECT_TIMEOUT)
            try:
                print(f"[PeerClient] Connecting to {peer_ip}:{peer_port}...")
                sock.connect((peer_ip, peer_port))
                print(f"[PeerClient] Connected! Sending {len(payload)} bytes...")
                sock.sendall(payload.encode("utf-8"))
                print(f"[PeerClient] ✓ Sent {message.msg_type} to {peer_ip}:{peer_port}")
                log.debug("Sent message %s to %s:%s", message.message_id, peer_ip, peer_port)
                return True
            except (OSError, ConnectionError) as exc:
                print(f"[PeerClient] ✗ Failed to send to {peer_ip}:{peer_port}: {exc}")
                # Don't log warning for connection refused (peer offline is normal)
                log.debug("Failed to send to %s:%s (peer may be offline)", peer_ip, peer_port)
                return False
