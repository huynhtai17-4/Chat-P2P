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

USELESS_IP_RANGES = [
    "169.254.",
]

VIRTUAL_ADAPTER_KEYWORDS = [
    "vethernet",
    "memu",
    "nox",
    "ldplayer",
    "bluestacks",
    "docker",
    "hyper-v",
    "wsl",
]

# VMware NAT default ranges to deprioritize
VMWARE_NAT_RANGES = [
    "192.168.40.",  # VMware NAT default
    "192.168.137.", # Windows Mobile Hotspot
    "192.168.56.",  # VirtualBox Host-Only
]

# Common LAN ranges (preferred)
COMMON_LAN_RANGES = [
    "192.168.0.",
    "192.168.1.",
    "192.168.2.",
    "10.0.0.",
    "10.0.1.",
]

def _is_virtual_adapter_by_name(adapter_name: str) -> bool:
    
    name_lower = adapter_name.lower()
    for keyword in VIRTUAL_ADAPTER_KEYWORDS:
        if keyword in name_lower:
            return True
    return False

def _is_useless_ip(ip: str) -> bool:
    
    for ip_range in USELESS_IP_RANGES:
        if ip.startswith(ip_range):
            return True
    return False

def _is_lan_ip(ip: str) -> bool:
    
    if ip == "127.0.0.1" or ip.startswith("127."):
        return False
    if _is_useless_ip(ip):
        return False
    
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    
    try:
        first = int(parts[0])
        second = int(parts[1])
        
        if first == 192 and second == 168:
            return True
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
                            log.debug("Found IP: %s (%s)", ip, interface_name)
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

def _is_vmware_nat_ip(ip: str) -> bool:
    """Check if IP is from VMware NAT or other virtual networks"""
    for vm_range in VMWARE_NAT_RANGES:
        if ip.startswith(vm_range):
            return True
    return False

def _is_common_lan_ip(ip: str) -> bool:
    """Check if IP is from common LAN ranges"""
    for lan_range in COMMON_LAN_RANGES:
        if ip.startswith(lan_range):
            return True
    return False

def _get_ip_subnet(ip: str) -> str:
    """Get subnet (first 3 octets) from IP"""
    parts = ip.split('.')
    if len(parts) >= 3:
        return f"{parts[0]}.{parts[1]}.{parts[2]}"
    return ""

def get_local_ip(network_mode: Optional[str] = None) -> str:
    all_ips = _get_all_network_ips()
    
    log.info("=" * 60)
    log.info("🌐 NETWORK DETECTION - Found %d network interfaces:", len(all_ips))
    for name, ip in all_ips:
        log.info("   - %s: %s", ip, name)
    log.info("=" * 60)
    
    if not all_ips:
        log.error("❌ No network interfaces found - check network connection!")
        return ""
    
    # Filter out useless IPs
    valid_ips = []
    vmware_nat_ips = []
    
    for name, ip in all_ips:
        if ip.startswith("127."):
            log.debug("Filtered out loopback: %s (%s)", ip, name)
            continue
        if _is_useless_ip(ip):
            log.debug("Filtered out useless IP: %s (%s)", ip, name)
            continue
        
        if _is_vmware_nat_ip(ip):
            vmware_nat_ips.append((name, ip))
            log.warning("⚠️  Detected VMware/Virtual NAT IP: %s (%s) - deprioritized", ip, name)
        else:
            valid_ips.append((name, ip))
    
    log.info("✓ Valid LAN IPs: %s", [f"{ip} ({name})" for name, ip in valid_ips])
    log.info("⚠  Virtual NAT IPs: %s", [f"{ip} ({name})" for name, ip in vmware_nat_ips])
    
    if not valid_ips and not vmware_nat_ips:
        log.error("❌ No valid network IPs found. All IPs: %s", all_ips)
        if all_ips:
            for name, ip in all_ips:
                if not ip.startswith("127."):
                    log.warning("⚠️  Using first non-loopback IP as last resort: %s (%s)", ip, name)
                    return ip
        return ""
    
    # Priority 1: Common LAN IPs (192.168.0.x, 192.168.1.x, 10.0.0.x)
    for name, ip in valid_ips:
        if _is_common_lan_ip(ip):
            log.info("✅ SELECTED: %s (%s) [Common LAN range - highest priority]", ip, name)
            return ip
    
    # Priority 2: WiFi/Ethernet with 192.168.x.x or 10.x.x.x
    wifi_priority = ["wi-fi", "wlan", "wireless"]
    ethernet_priority = ["ethernet", "eth", "lan"]
    
    for name, ip in valid_ips:
        name_lower = name.lower()
        if any(keyword in name_lower for keyword in wifi_priority):
            if ip.startswith("192.168.") or ip.startswith("10."):
                log.info("✅ SELECTED: %s (%s) [WiFi adapter]", ip, name)
                return ip
    
    for name, ip in valid_ips:
        name_lower = name.lower()
        if any(keyword in name_lower for keyword in ethernet_priority):
            if ip.startswith("192.168.") or ip.startswith("10."):
                log.info("✅ SELECTED: %s (%s) [Ethernet adapter]", ip, name)
                return ip
    
    # Priority 3: Any 192.168.x.x (but not VMware NAT)
    for name, ip in valid_ips:
        if ip.startswith("192.168."):
            log.info("✅ SELECTED: %s (%s) [Private IP 192.168.x.x]", ip, name)
            return ip
    
    # Priority 4: 10.x.x.x
    for name, ip in valid_ips:
        if ip.startswith("10."):
            log.info("✅ SELECTED: %s (%s) [Private IP 10.x.x.x]", ip, name)
            return ip
    
    # Priority 5: 172.16-31.x.x
    for name, ip in valid_ips:
        if ip.startswith("172."):
            try:
                second_octet = int(ip.split('.')[1])
                if 16 <= second_octet <= 31:
                    log.info("✅ SELECTED: %s (%s) [Private IP 172.16-31.x.x]", ip, name)
                    return ip
            except (ValueError, IndexError):
                continue
    
    # Priority 6: CGNAT 100.64-127.x.x
    for name, ip in valid_ips:
        if ip.startswith("100."):
            try:
                second_octet = int(ip.split('.')[1])
                if 64 <= second_octet <= 127:
                    log.info("✅ SELECTED: %s (%s) [CGNAT IP]", ip, name)
                    return ip
            except (ValueError, IndexError):
                continue
    
    # Priority 7: Any other valid IP
    if valid_ips:
        name, ip = valid_ips[0]
        log.info("✅ SELECTED: %s (%s) [First valid IP]", ip, name)
        return ip
    
    # Last resort: Use VMware NAT IP if nothing else available
    if vmware_nat_ips:
        name, ip = vmware_nat_ips[0]
        log.warning("⚠️  SELECTED: %s (%s) [VMware NAT - last resort]", ip, name)
        log.warning("⚠️  WARNING: You may not be able to connect to peers on different networks!")
        log.warning("⚠️  SOLUTION: Change VMware network to 'Bridged' mode for LAN connectivity")
        return ip
    
    log.error("❌ No valid network IP found")
    return ""
