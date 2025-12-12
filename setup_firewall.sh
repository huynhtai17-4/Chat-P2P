#!/bin/bash

echo "=== Chat P2P - Firewall Setup for Linux ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use: sudo bash setup_firewall.sh)"
    exit 1
fi

# Detect firewall
if command -v ufw &> /dev/null; then
    echo "[UFW] Detected UFW firewall"
    ufw allow 55000:55199/tcp comment "Chat P2P TCP"
    ufw allow 55000:55199/udp comment "Chat P2P UDP (calls)"
    echo "[UFW] Opened ports 55000-55199 TCP/UDP"
    
elif command -v firewall-cmd &> /dev/null; then
    echo "[firewalld] Detected firewalld"
    firewall-cmd --permanent --add-port=55000-55199/tcp
    firewall-cmd --permanent --add-port=55000-55199/udp
    firewall-cmd --reload
    echo "[firewalld] Opened ports 55000-55199 TCP/UDP"
    
elif command -v iptables &> /dev/null; then
    echo "[iptables] Detected iptables"
    iptables -I INPUT -p tcp --dport 55000:55199 -j ACCEPT
    iptables -I INPUT -p udp --dport 55000:55199 -j ACCEPT
    
    # Try to save rules (Kali uses nftables backend)
    if command -v iptables-save &> /dev/null; then
        if [ -d /etc/iptables ]; then
            iptables-save > /etc/iptables/rules.v4 2>/dev/null && echo "[iptables] Rules saved to /etc/iptables/rules.v4"
        elif [ -f /etc/sysconfig/iptables ]; then
            iptables-save > /etc/sysconfig/iptables 2>/dev/null && echo "[iptables] Rules saved to /etc/sysconfig/iptables"
        else
            echo "[iptables] Rules applied (will reset after reboot)"
            echo "[iptables] To make persistent, install iptables-persistent:"
            echo "           sudo apt-get install iptables-persistent"
            echo "           sudo netfilter-persistent save"
        fi
    fi
    echo "[iptables] Opened ports 55000-55199 TCP/UDP"
    
else
    echo "[WARNING] No firewall detected or already disabled"
fi

echo ""
echo "=== Setup Complete! ==="
echo "Ports 55000-55199 (TCP/UDP) are now open for Chat P2P"
echo ""
echo "To check firewall status:"
echo "  - UFW:       sudo ufw status"
echo "  - firewalld: sudo firewall-cmd --list-all"
echo "  - iptables:  sudo iptables -L -n"

