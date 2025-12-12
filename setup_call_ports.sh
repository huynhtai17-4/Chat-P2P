#!/bin/bash

echo "=== Chat P2P - Call Ports Setup (UDP) ==="
echo "Opening UDP ports 56000-57000 for audio/video calls"
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use: sudo bash setup_call_ports.sh)"
    exit 1
fi

if command -v ufw &> /dev/null; then
    echo "[UFW] Opening UDP ports..."
    ufw allow 56000:57000/udp comment "Chat P2P Calls"
    echo "[UFW] ✓ Opened UDP ports 56000-57000"
    
elif command -v firewall-cmd &> /dev/null; then
    echo "[firewalld] Opening UDP ports..."
    firewall-cmd --permanent --add-port=56000-57000/udp
    firewall-cmd --reload
    echo "[firewalld] ✓ Opened UDP ports 56000-57000"
    
elif command -v iptables &> /dev/null; then
    echo "[iptables] Opening UDP ports..."
    iptables -I INPUT -p udp --dport 56000:57000 -j ACCEPT
    
    if [ -d /etc/iptables ]; then
        iptables-save > /etc/iptables/rules.v4 2>/dev/null && echo "[iptables] Rules saved"
    elif [ -f /etc/sysconfig/iptables ]; then
        iptables-save > /etc/sysconfig/iptables 2>/dev/null && echo "[iptables] Rules saved"
    else
        echo "[iptables] Rules applied (may reset after reboot)"
    fi
    echo "[iptables] ✓ Opened UDP ports 56000-57000"
else
    echo "[WARNING] No firewall detected"
fi

echo ""
echo "=== Setup Complete! ==="
echo "UDP ports 56000-57000 are now open for calls"
echo ""
echo "Note: TCP port 55000-55199 should also be open for messages"
echo "Run: sudo bash setup_firewall.sh (if not done already)"

