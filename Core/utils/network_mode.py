from __future__ import annotations

import logging
import os
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
    "192.168.234.",  # VMware
    "192.168.235.",  # VMware NAT
    "192.168.56.",   # VirtualBox
    "192.168.122.",  # libvirt
    "169.254.",      # Link-local
]

NETWORK_MODE_SINGLE = "single_machine"
NETWORK_MODE_LAN = "lan"

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
            log.warning("Failed to enumerate network interfaces with psutil: %s", e)
    else:
        # Fallback: Read from system commands or socket.getaddrinfo
        print("[Network] psutil not available, using fallback IP detection")
        
        # Try to read from `ip addr` command on Linux
        if platform.system() == "Linux":
            try:
                print("[Network] Trying `ip addr` command...")
                result = subprocess.run(
                    ["ip", "addr", "show"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    import re
                    # Parse output: inet 192.168.x.x/24 ...
                    lines = result.stdout.split('\n')
                    current_interface = None
                    for line in lines:
                        # Match interface name
                        if_match = re.match(r'^\d+:\s+(\S+):', line)
                        if if_match:
                            current_interface = if_match.group(1)
                        # Match inet address
                        inet_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', line)
                        if inet_match and current_interface:
                            ip = inet_match.group(1)
                            if ip and ip != "127.0.0.1" and not ip.startswith("127."):
                                print(f"[Network] Found IP from `ip addr`: {ip} ({current_interface})")
                                ips.append((current_interface, ip))
            except Exception as e:
                print(f"[Network] `ip addr` command failed: {e}")
        
        # Try hostname resolution
        try:
            hostname = socket.gethostname()
            print(f"[Network] Hostname: {hostname}")
            
            # Get all IPs associated with hostname
            try:
                addr_infos = socket.getaddrinfo(hostname, None, socket.AF_INET)
                for addr_info in addr_infos:
                    ip = addr_info[4][0]
                    if ip and ip != "127.0.0.1" and not ip.startswith("127."):
                        print(f"[Network] Found IP from hostname: {ip}")
                        # Only add if not already in list
                        if not any(existing_ip == ip for _, existing_ip in ips):
                            ips.append(("hostname", ip))
            except Exception as e:
                print(f"[Network] getaddrinfo failed: {e}")
            
            # Also try socket trick (may return NAT IP but better than nothing)
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("8.8.8.8", 80))
                    ip = s.getsockname()[0]
                    if ip and ip != "127.0.0.1":
                        print(f"[Network] Found IP from socket trick: {ip}")
                        # Only add if not already in list
                        if not any(existing_ip == ip for _, existing_ip in ips):
                            ips.append(("socket", ip))
            except Exception as e:
                print(f"[Network] Socket trick failed: {e}")
                
        except Exception as e:
            print(f"[Network] Fallback IP detection failed: {e}")
            log.warning("Failed to get network IP with fallback: %s", e)
    
    print(f"[Network] Found {len(ips)} IPs: {[ip for _, ip in ips]}")
    return ips

def _count_running_instances() -> int:
    
    count = 0
    
    if PSUTIL_AVAILABLE:
        try:
            current_pid = os.getpid()
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['pid'] == current_pid:
                        continue
                    
                    cmdline = proc.info.get('cmdline', [])
                    if not cmdline:
                        continue
                    
                    cmdline_str = ' '.join(cmdline).lower()
                    if 'python' in cmdline_str and 'main.py' in cmdline_str:
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            log.warning("Failed to count running instances with psutil: %s", e)
    else:
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                lines = result.stdout.lower().split('\n')
                count = sum(1 for line in lines if 'main.py' in line)
                if count > 0:
                    count -= 1
            else:
                result = subprocess.run(
                    ["ps", "aux"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                lines = result.stdout.lower().split('\n')
                count = sum(1 for line in lines if 'main.py' in line and 'python' in line)
                if count > 0:
                    count -= 1
        except Exception as e:
            log.warning("Failed to count running instances with fallback: %s", e)
    
    return max(0, count)

def detect_network_mode() -> str:
    
    instance_count = _count_running_instances()
    if instance_count > 0:
        log.info("Detected %s other instance(s) running - using single-machine mode", instance_count)
        return NETWORK_MODE_SINGLE
    
    all_ips = _get_all_network_ips()
    
    lan_ips = [(name, ip) for name, ip in all_ips if _is_lan_ip(ip)]
    
    if not lan_ips:
        log.info("No valid LAN IPs found (only virtual adapters or localhost) - using single-machine mode")
        return NETWORK_MODE_SINGLE
    
    log.info("Detected LAN mode with %s valid IP(s): %s", len(lan_ips), [ip for _, ip in lan_ips])
    return NETWORK_MODE_LAN

def get_local_ip(network_mode: Optional[str] = None) -> str:
    """Get local IP address - prioritize private IP over public/localhost"""
    all_ips = _get_all_network_ips()
    
    if not all_ips:
        log.warning("No network interfaces found, falling back to 127.0.0.1")
        return "127.0.0.1"
    
    # Filter out virtual adapters and localhost
    valid_ips = []
    for name, ip in all_ips:
        if not _is_virtual_adapter(ip):
            valid_ips.append((name, ip))
    
    if not valid_ips:
        log.warning("Only virtual adapters found, falling back to 127.0.0.1")
        return "127.0.0.1"
    
    # Prioritize private IPs (RFC 1918)
    # 1. 192.168.x.x (most common home/office)
    for name, ip in valid_ips:
        if ip.startswith("192.168."):
            log.info("Selected private IP (192.168.x.x): %s (%s)", ip, name)
            return ip
    
    # 2. 10.x.x.x
    for name, ip in valid_ips:
        if ip.startswith("10."):
            log.info("Selected private IP (10.x.x.x): %s (%s)", ip, name)
            return ip
    
    # 3. 172.16-31.x.x
    for name, ip in valid_ips:
        if ip.startswith("172."):
            try:
                second_octet = int(ip.split('.')[1])
                if 16 <= second_octet <= 31:
                    log.info("Selected private IP (172.16-31.x.x): %s (%s)", ip, name)
                    return ip
            except (ValueError, IndexError):
                continue
    
    # 4. CGNAT range 100.64.0.0/10 (Carrier-Grade NAT - RFC 6598)
    for name, ip in valid_ips:
        if ip.startswith("100."):
            try:
                second_octet = int(ip.split('.')[1])
                if 64 <= second_octet <= 127:
                    log.info("Selected CGNAT IP (100.64-127.x.x): %s (%s)", ip, name)
                    return ip
            except (ValueError, IndexError):
                continue
    
    # 5. If any other non-localhost IP exists (could be public IP)
    for name, ip in valid_ips:
        if not ip.startswith("127."):
            log.info("Selected IP (public or other): %s (%s)", ip, name)
            return ip
    
    # Last resort: localhost
    log.warning("No valid network IP found, falling back to 127.0.0.1 (localhost only)")
    return "127.0.0.1"

def get_broadcast_address(network_mode: Optional[str] = None) -> str:
    
    if network_mode is None:
        network_mode = detect_network_mode()
    
    if network_mode == NETWORK_MODE_SINGLE:
        return "127.0.0.1"
    
    return "255.255.255.255"
