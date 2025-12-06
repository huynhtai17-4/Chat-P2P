"""
Network mode detection and IP selection utilities.
Handles single-machine mode (localhost) vs LAN mode.
"""

from __future__ import annotations

import logging
import os
import platform
import socket
import subprocess
from typing import List, Optional, Tuple

log = logging.getLogger(__name__)

# Try to import psutil, but provide fallback if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    log.warning("psutil not available, using fallback network detection")

# Virtual adapter IP ranges to ignore
VMWARE_NETWORKS = [
    "192.168.234.",  # VMware
    "192.168.56.",   # VirtualBox
    "192.168.122.",  # libvirt
    "169.254.",      # Link-local
]

NETWORK_MODE_SINGLE = "single_machine"
NETWORK_MODE_LAN = "lan"


def _is_virtual_adapter(ip: str) -> bool:
    """Check if IP belongs to a virtual adapter (VMware/VirtualBox)."""
    for network in VMWARE_NETWORKS:
        if ip.startswith(network):
            return True
    return False


def _is_lan_ip(ip: str) -> bool:
    """Check if IP is a valid LAN IP (not localhost, not virtual)."""
    if ip == "127.0.0.1" or ip.startswith("127."):
        return False
    if _is_virtual_adapter(ip):
        return False
    
    # Check for private IP ranges
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    
    try:
        first = int(parts[0])
        second = int(parts[1])
        
        # 192.168.x.x (excluding virtual adapters)
        if first == 192 and second == 168:
            return not _is_virtual_adapter(ip)
        # 10.x.x.x
        if first == 10:
            return True
        # 172.16-31.x.x
        if first == 172 and 16 <= second <= 31:
            return True
    except ValueError:
        return False
    
    return False


def _get_all_network_ips() -> List[Tuple[str, str]]:
    """
    Get all network interface IPs.
    Returns list of (interface_name, ip_address) tuples.
    """
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
        # Fallback: Use socket to get local IP
        try:
            # Try to connect to external address to get local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                if ip and ip != "127.0.0.1":
                    ips.append(("default", ip))
        except Exception as e:
            log.warning("Failed to get network IP with fallback: %s", e)
    
    return ips


def _count_running_instances() -> int:
    """Count how many instances of this app are running."""
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
                    
                    # Check if it's a Python process running main.py
                    cmdline_str = ' '.join(cmdline).lower()
                    if 'python' in cmdline_str and 'main.py' in cmdline_str:
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            log.warning("Failed to count running instances with psutil: %s", e)
    else:
        # Fallback: Use tasklist (Windows) or ps (Linux/Mac)
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                # Count lines containing "main.py"
                lines = result.stdout.lower().split('\n')
                count = sum(1 for line in lines if 'main.py' in line)
                # Subtract 1 for current process
                if count > 0:
                    count -= 1
            else:
                # Linux/Mac: use ps
                result = subprocess.run(
                    ["ps", "aux"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                lines = result.stdout.lower().split('\n')
                count = sum(1 for line in lines if 'main.py' in line and 'python' in line)
                # Subtract 1 for current process
                if count > 0:
                    count -= 1
        except Exception as e:
            log.warning("Failed to count running instances with fallback: %s", e)
    
    return max(0, count)


def detect_network_mode() -> str:
    """
    Detect network mode: single_machine or lan.
    
    Returns:
        "single_machine" if multiple instances on same machine or only virtual adapters
        "lan" if valid LAN IP exists and no multiple instances detected
    """
    # Check for multiple instances
    instance_count = _count_running_instances()
    if instance_count > 0:
        log.info("Detected %s other instance(s) running - using single-machine mode", instance_count)
        return NETWORK_MODE_SINGLE
    
    # Get all network IPs
    all_ips = _get_all_network_ips()
    
    # Filter to LAN IPs only
    lan_ips = [(name, ip) for name, ip in all_ips if _is_lan_ip(ip)]
    
    # If no valid LAN IPs, use single-machine mode
    if not lan_ips:
        log.info("No valid LAN IPs found (only virtual adapters or localhost) - using single-machine mode")
        return NETWORK_MODE_SINGLE
    
    # If we have valid LAN IPs and no multiple instances, use LAN mode
    log.info("Detected LAN mode with %s valid IP(s): %s", len(lan_ips), [ip for _, ip in lan_ips])
    return NETWORK_MODE_LAN


def get_local_ip(network_mode: Optional[str] = None) -> str:
    """
    Get the appropriate local IP based on network mode.
    
    Args:
        network_mode: "single_machine" or "lan". If None, auto-detects.
        
    Returns:
        "127.0.0.1" for single-machine mode
        Valid LAN IP for LAN mode
    """
    if network_mode is None:
        network_mode = detect_network_mode()
    
    if network_mode == NETWORK_MODE_SINGLE:
        return "127.0.0.1"
    
    # LAN mode: find best LAN IP
    all_ips = _get_all_network_ips()
    lan_ips = [(name, ip) for name, ip in all_ips if _is_lan_ip(ip)]
    
    if not lan_ips:
        log.warning("LAN mode but no valid LAN IP found, falling back to 127.0.0.1")
        return "127.0.0.1"
    
    # Prefer 192.168.x.x, then 10.x.x.x, then 172.16-31.x.x
    for name, ip in lan_ips:
        if ip.startswith("192.168."):
            log.info("Selected LAN IP: %s (%s)", ip, name)
            return ip
    
    for name, ip in lan_ips:
        if ip.startswith("10."):
            log.info("Selected LAN IP: %s (%s)", ip, name)
            return ip
    
    for name, ip in lan_ips:
        if ip.startswith("172."):
            log.info("Selected LAN IP: %s (%s)", ip, name)
            return ip
    
    # Fallback to first LAN IP
    ip = lan_ips[0][1]
    log.info("Selected LAN IP: %s (%s)", ip, lan_ips[0][0])
    return ip


def get_broadcast_address(network_mode: Optional[str] = None) -> str:
    """
    Get the appropriate broadcast address based on network mode.
    
    Args:
        network_mode: "single_machine" or "lan". If None, auto-detects.
        
    Returns:
        "127.0.0.1" for single-machine mode (localhost broadcast)
        "255.255.255.255" for LAN mode (full broadcast)
    """
    if network_mode is None:
        network_mode = detect_network_mode()
    
    if network_mode == NETWORK_MODE_SINGLE:
        return "127.0.0.1"
    
    return "255.255.255.255"

