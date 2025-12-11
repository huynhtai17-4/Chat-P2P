from __future__ import annotations

import logging
import socket

from Core.models.message import Message
from Core.utils import config

log = logging.getLogger(__name__)

class PeerClient:

    def send(self, peer_ip: str, peer_port: int, message: Message) -> bool:
        payload = message.to_json() + "\n"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(config.TCP_CONNECT_TIMEOUT)
            try:
                sock.connect((peer_ip, peer_port))
                sock.sendall(payload.encode("utf-8"))
                log.debug("Sent message %s to %s:%s", message.message_id, peer_ip, peer_port)
                return True
            except (OSError, ConnectionError) as exc:
                log.debug("Failed to send to %s:%s (peer may be offline)", peer_ip, peer_port)
                return False