#!/bin/bash

echo "=== Chat P2P - Network Check ==="
echo ""

# Check IP address
echo "1. Your IP addresses:"
if command -v ip &> /dev/null; then
    ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v 127.0.0.1
elif command -v ifconfig &> /dev/null; then
    ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}'
else
    echo "   Cannot detect IP (install 'iproute2' or 'net-tools')"
fi

echo ""
echo "2. Checking if port 55000 is listening..."
if command -v ss &> /dev/null; then
    ss -tuln | grep :55000 && echo "   ✓ Port 55000 is LISTENING" || echo "   ✗ Port 55000 is NOT listening (app not running?)"
elif command -v netstat &> /dev/null; then
    netstat -tuln | grep :55000 && echo "   ✓ Port 55000 is LISTENING" || echo "   ✗ Port 55000 is NOT listening (app not running?)"
else
    echo "   Cannot check (install 'iproute2' or 'net-tools')"
fi

echo ""
echo "3. Firewall status:"
if command -v ufw &> /dev/null; then
    echo "   [UFW]"
    sudo ufw status 2>/dev/null | grep -E "(Status|55000)" || echo "   UFW is inactive"
elif command -v firewall-cmd &> /dev/null; then
    echo "   [firewalld]"
    sudo firewall-cmd --list-ports 2>/dev/null | grep 55000 && echo "   ✓ Port 55000 is OPEN" || echo "   ✗ Port 55000 is NOT open"
elif command -v iptables &> /dev/null; then
    echo "   [iptables]"
    sudo iptables -L INPUT -n 2>/dev/null | grep -E "55000|ACCEPT.*tcp" | head -3 || echo "   (Run with sudo to check iptables)"
else
    echo "   No firewall detected or not running"
fi

echo ""
echo "4. Network connectivity:"
ping -c 2 -W 2 8.8.8.8 > /dev/null 2>&1 && echo "   ✓ Internet is reachable" || echo "   ✗ No internet connection"

echo ""
echo "5. IP Analysis:"
for ip in $(ip -4 addr show 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v 127.0.0.1); do
    if [[ $ip == 192.168.40.* ]] || [[ $ip == 192.168.56.* ]] || [[ $ip == 192.168.235.* ]]; then
        echo "   ⚠ $ip - VMware NAT (may not work with physical machines)"
    elif [[ $ip == 192.168.1.* ]] || [[ $ip == 192.168.0.* ]]; then
        echo "   ✓ $ip - LAN IP (good for P2P)"
    else
        echo "   ? $ip - Unknown network"
    fi
done

echo ""
echo "=== Troubleshooting ==="
echo "If peer cannot connect to you:"
echo "  1. Run app and check port is listening"
echo "  2. Open firewall: sudo bash setup_firewall.sh"
echo "  3. Check router/NAT allows LAN connections"
echo "  4. Use correct IP from section 1 above"

