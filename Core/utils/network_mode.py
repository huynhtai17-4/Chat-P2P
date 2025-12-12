from __future__ import annotations

import logging
import platform
import socket
import subprocess
from typing import List, Optional, Tuple

log = logging.getLogger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    log.warning("psutil not available, using fallback network detection")

VMWARE_NETWORKS = [
    "192.168.234.",
    "192.168.235.",
    "192.168.56.",
    "192.168.122.",
    "169.254.",
] # Danh sách IP ảo loại bỏ

def _is_virtual_adapter(ip: str) -> bool:
    
    for network in VMWARE_NETWORKS:
        if ip.startswith(network):
            return True
    return False

def _is_lan_ip(ip: str) -> bool:
    
    if ip == "127.0.0.1" or ip.startswith("127."):
        return False
    if _is_virtual_adapter(ip):
        return False
    
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    
    try:
        first = int(parts[0])
        second = int(parts[1])
        
        if first == 192 and second == 168:
            return not _is_virtual_adapter(ip)
        if first == 10:
            return True
        if first == 172 and 16 <= second <= 31:
            return True
    except ValueError:
        return False
    
    return False

def _get_all_network_ips() -> List[Tuple[str, str]]:
    
    ips = []
    
    if PSUTIL_AVAILABLE:
        try:
            interfaces = psutil.net_if_addrs()
            for interface_name, addrs in interfaces.items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        ip = addr.address
                        if ip and ip != "127.0.0.1":
                            ips.append((interface_name, ip))
        except Exception as e:
            log.warning("Khong the lay danh sach IP cua mang bang psutil: %s", e)
    else:
        log.debug("psutil khong co san, su dung phuong phap fallback de lay danh sach IP")
        
        if platform.system() == "Linux":
            try:
                result = subprocess.run(
                    ["ip", "addr", "show"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    import re
                    lines = result.stdout.split('\n')
                    current_interface = None
                    for line in lines:
                        if_match = re.match(r'^\d+:\s+(\S+):', line)
                        if if_match:
                            current_interface = if_match.group(1)
                        inet_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', line)
                        if inet_match and current_interface:
                            ip = inet_match.group(1)
                            if ip and ip != "127.0.0.1" and not ip.startswith("127."):
                                ips.append((current_interface, ip))
            except Exception as e:
                log.debug(f"`ip addr` lệnh thất b: {e}")
        
        try:
            hostname = socket.gethostname()
            
            try:
                addr_infos = socket.getaddrinfo(hostname, None, socket.AF_INET)
                for addr_info in addr_infos:
                    ip = addr_info[4][0]
                    if ip and ip != "127.0.0.1" and not ip.startswith("127."):
                        if not any(existing_ip == ip for _, existing_ip in ips):
                            ips.append(("hostname", ip))
            except Exception as e:
                log.debug(f"getaddrinfo failed: {e}")
            
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("8.8.8.8", 80))
                    ip = s.getsockname()[0]
                    if ip and ip != "127.0.0.1":
                        if not any(existing_ip == ip for _, existing_ip in ips):
                            ips.append(("socket", ip))
            except Exception as e:
                log.debug(f"Socket trick failed: {e}")
                
        except Exception as e:
            log.warning("Failed to get network IP with fallback: %s", e)
    
    return ips

def get_local_ip(network_mode: Optional[str] = None) -> str:
    all_ips = _get_all_network_ips()
    
    if not all_ips:
        log.warning("No network interfaces found")
        return ""
    
    valid_ips = []
    for name, ip in all_ips:
        if not _is_virtual_adapter(ip) and not ip.startswith("127."):
            valid_ips.append((name, ip))
    
    if not valid_ips:
        log.warning("Only virtual adapters found")
        return ""
    
    for name, ip in valid_ips:
        if ip.startswith("192.168."):
            log.info("Selected private IP (192.168.x.x): %s (%s)", ip, name)
            return ip
    
    for name, ip in valid_ips:
        if ip.startswith("10."):
            log.info("Selected private IP (10.x.x.x): %s (%s)", ip, name)
            return ip
    
    for name, ip in valid_ips:
        if ip.startswith("172."):
            try:
                second_octet = int(ip.split('.')[1])
                if 16 <= second_octet <= 31:
                    log.info("Selected private IP (172.16-31.x.x): %s (%s)", ip, name)
                    return ip
            except (ValueError, IndexError):
                continue
    
    for name, ip in valid_ips:
        if ip.startswith("100."):
            try:
                second_octet = int(ip.split('.')[1])
                if 64 <= second_octet <= 127:
                    log.info("Selected CGNAT IP (100.64-127.x.x): %s (%s)", ip, name)
                    return ip
            except (ValueError, IndexError):
                continue
    
    for name, ip in valid_ips:
        log.info("Selected IP (public or other): %s (%s)", ip, name)
        return ip
    
    log.warning("No valid network IP found")
    return ""
