from __future__ import annotations

import logging
import platform
import socket
import subprocess
from typing import List, Tuple

log = logging.getLogger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    log.warning("psutil not available, using fallback network detection")

# IP ranges and adapter keywords
USELESS_IP_RANGES = ["169.254."]
VIRTUAL_NAT_RANGES = ["192.168.40.", "192.168.137.", "192.168.56.", "172.20.", "192.168.50."]
COMMON_LAN_RANGES = ["192.168.0.", "192.168.1.", "192.168.2.", "10.0.0.", "10.0.1."]

VIRTUAL_ADAPTER_KEYWORDS = [
    "vmware", "virtualbox", "vbox", "vethernet", "hyper-v", "wsl", "docker", 
    "loopback", "pseudo", "microsoft wi-fi direct", "bluetooth", "mobile hotspot"
]
REAL_ADAPTER_KEYWORDS = ["wi-fi", "wireless", "wlan", "802.11", "ethernet", "eth", "lan"]

def _get_all_network_ips() -> List[Tuple[str, str]]:
    """Get all available IPv4 addresses with their interface names."""
    ips = []
    if PSUTIL_AVAILABLE:
        try:
            for name, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and addr.address != "127.0.0.1":
                        ips.append((name, addr.address))
        except Exception as e:
            log.warning(f"psutil failed: {e}")
            
    if not ips: # Fallback
        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
                ip = info[4][0]
                if ip != "127.0.0.1" and not any(x[1] == ip for x in ips):
                    ips.append(("hostname", ip))
            
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                if ip != "127.0.0.1" and not any(x[1] == ip for x in ips):
                    ips.append(("socket", ip))
        except: pass
    return ips

def _is_virtual(name: str, ip: str) -> bool:
    name_l = name.lower()
    return any(k in name_l for k in VIRTUAL_ADAPTER_KEYWORDS) or any(ip.startswith(r) for r in VIRTUAL_NAT_RANGES)

def _is_real(name: str) -> bool:
    return any(k in name.lower() for k in REAL_ADAPTER_KEYWORDS)

def get_local_ip() -> str:
    """Detect and return the best local IP for P2P communication."""
    all_ips = _get_all_network_ips()
    if not all_ips: return ""

    real_ips, other_ips, virtual_ips = [], [], []
    for name, ip in all_ips:
        if any(ip.startswith(r) for r in USELESS_IP_RANGES): continue
        if _is_real(name): 
            real_ips.append((name, ip))
        elif _is_virtual(name, ip): 
            virtual_ips.append((name, ip))
        else: 
            other_ips.append((name, ip))

    # Selection Priority
    for group in [real_ips, other_ips, virtual_ips]:
        for name, ip in group:
            if any(ip.startswith(r) for r in COMMON_LAN_RANGES):
                log.info(f"SELECTED: {ip} ({name})")
                return ip
        for name, ip in group:
            if ip.startswith(("192.168.", "10.")):
                log.info(f"SELECTED: {ip} ({name})")
                return ip
        if group:
            log.info(f"SELECTED: {group[0][1]} ({group[0][0]})")
            return group[0][1]

    return all_ips[0][1] if all_ips else ""
