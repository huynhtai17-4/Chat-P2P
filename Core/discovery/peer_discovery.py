from __future__ import annotations

import json
import logging
import socket
import threading
import time
from typing import Callable, Optional

from Core.models.peer_info import PeerInfo
from Core.storage.data_manager import DataManager
from Core.utils import config
from Core.utils.network_mode import (
    detect_network_mode,
    get_local_ip,
    get_broadcast_address,
    NETWORK_MODE_SINGLE,
)

log = logging.getLogger(__name__)

class PeerDiscovery:

    def __init__(
        self,
        peer_id: str,
        display_name: str,
        tcp_port: int,
        data_manager: DataManager,
        on_peer_found: Optional[Callable[[PeerInfo], None]] = None,
    ):
        self.peer_id = peer_id
        self.display_name = display_name
        self.tcp_port = tcp_port
        self.data_manager = data_manager
        self.on_peer_found = on_peer_found

        self._stop_event = threading.Event()
        self._broadcast_thread: Optional[threading.Thread] = None
        self._listen_thread: Optional[threading.Thread] = None
        
        self._network_mode = detect_network_mode()
        self._local_ip = get_local_ip(self._network_mode)
        self._broadcast_addr = get_broadcast_address(self._network_mode)
        
        log.info("PeerDiscovery initialized: mode=%s, local_ip=%s, broadcast=%s, tcp_port=%s",
                self._network_mode, self._local_ip, self._broadcast_addr, self.tcp_port)

    def start(self):
        if self._broadcast_thread and self._broadcast_thread.is_alive():
            return
        self._stop_event.clear()
        self._broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True, name="PeerDiscoveryBroadcast")
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True, name="PeerDiscoveryListen")
        self._broadcast_thread.start()
        self._listen_thread.start()
        log.info("PeerDiscovery started (UDP port %s, mode=%s)", config.UDP_DISCOVERY_PORT, self._network_mode)

    def stop(self):
        self._stop_event.set()

    def _broadcast_loop(self):
        payload = {
            "type": config.DISCOVERY_PACKET_TYPE,
            "peer_id": self.peer_id,
            "display_name": self.display_name,
            "tcp_port": self.tcp_port,  # MUST be included
            "ip": self._local_ip,       # include sender IP for LAN mode
        }
        log.info("[Discovery] Broadcasting as %s (%s) on %s:%s, tcp_port=%s", 
                self.display_name, self.peer_id, self._broadcast_addr, config.UDP_DISCOVERY_PORT, self.tcp_port)
        
        while not self._stop_event.is_set():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.settimeout(0.2)
                    sock.sendto(json.dumps(payload).encode("utf-8"), (self._broadcast_addr, config.UDP_DISCOVERY_PORT))
                    log.debug("[Discovery] Broadcast sent to %s:%s", self._broadcast_addr, config.UDP_DISCOVERY_PORT)
            except OSError as exc:
                log.warning("[Discovery] Broadcast failed: %s", exc)
            self._stop_event.wait(config.UDP_DISCOVERY_INTERVAL)

    def _listen_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", config.UDP_DISCOVERY_PORT))
            sock.settimeout(config.UDP_DISCOVERY_TIMEOUT)
            log.info("[Discovery] Listening on UDP port %s", config.UDP_DISCOVERY_PORT)
        except OSError as exc:
            log.error("[Discovery] Failed to bind discovery socket on port %s: %s", config.UDP_DISCOVERY_PORT, exc)
            return

        with sock:
            while not self._stop_event.is_set():
                try:
                    data, (ip, _) = sock.recvfrom(1024)
                except socket.timeout:
                    continue
                except OSError:
                    break

                try:
                    packet = json.loads(data.decode("utf-8"))
                except json.JSONDecodeError:
                    log.debug("[Discovery] Received invalid JSON from %s", ip)
                    continue

                if packet.get("type") != config.DISCOVERY_PACKET_TYPE:
                    continue
                if packet.get("peer_id") == self.peer_id:
                    continue  # ignore self
                
                log.info("[Discovery] Received from %s: %s (%s) tcp_port=%s", 
                        ip, packet.get("display_name"), packet.get("peer_id"), packet.get("tcp_port"))

                tcp_port = packet.get("tcp_port")
                if not tcp_port or not isinstance(tcp_port, (int, str)):
                    log.warning("Discovery packet missing tcp_port from %s, skipping", packet.get("peer_id"))
                    continue
                
                try:
                    tcp_port = int(tcp_port)
                except (ValueError, TypeError):
                    log.warning("Invalid tcp_port in discovery packet from %s: %s", packet.get("peer_id"), tcp_port)
                    continue
                
                if tcp_port < 55000 or tcp_port > 55199:
                    log.warning("Discovery packet has invalid tcp_port %s from %s (must be 55000-55199), skipping",
                               tcp_port, packet.get("peer_id"))
                    continue
                
                if self._network_mode == NETWORK_MODE_SINGLE:
                    peer_ip = "127.0.0.1"
                else:
                    peer_ip = packet.get("ip") or ip or self._local_ip
                    if peer_ip.startswith("192.168.234.") or peer_ip.startswith("192.168.56."):
                        log.debug("Ignoring discovery from virtual adapter IP: %s", peer_ip)
                        continue

                peer_info = PeerInfo(
                    peer_id=packet["peer_id"],
                    display_name=packet.get("display_name", "Unknown"),
                    ip=peer_ip,
                    tcp_port=tcp_port,  # From discovery packet (authoritative)
                    last_seen=time.time(),
                    status="offline",  # discovery does not imply online; wait for ONLINE event
                )
                
                if self.on_peer_found:
                    try:
                        self.on_peer_found(peer_info)
                    except Exception as e:
                        log.error("Error in on_peer_found callback for %s: %s", peer_info.peer_id, e, exc_info=True)
