#!/bin/bash

echo "=== Chat P2P - Connection Test ==="
echo ""

if [ -z "$1" ]; then
    echo "Usage: bash test_connection.sh <peer_ip> [port]"
    echo "Example: bash test_connection.sh 192.168.1.80 55000"
    exit 1
fi

PEER_IP=$1
PEER_PORT=${2:-55000}

echo "Testing connection to $PEER_IP:$PEER_PORT"
echo ""

# Ping test
echo "1. Ping test:"
if ping -c 2 -W 2 "$PEER_IP" > /dev/null 2>&1; then
    echo "   ✓ Host is reachable"
else
    echo "   ✗ Host is NOT reachable (check IP and network)"
    exit 1
fi

# TCP connection test
echo ""
echo "2. TCP connection test:"
if command -v nc &> /dev/null; then
    if timeout 3 nc -zv "$PEER_IP" "$PEER_PORT" 2>&1 | grep -q "succeeded\|open"; then
        echo "   ✓ Port $PEER_PORT is OPEN and accepting connections"
    else
        echo "   ✗ Port $PEER_PORT is CLOSED or not responding"
        echo "   → Check if peer's app is running"
        echo "   → Check if peer's firewall allows port $PEER_PORT"
    fi
elif command -v telnet &> /dev/null; then
    timeout 3 telnet "$PEER_IP" "$PEER_PORT" 2>&1 | grep -q "Connected\|Escape" && \
        echo "   ✓ Port $PEER_PORT is OPEN" || \
        echo "   ✗ Port $PEER_PORT is CLOSED"
else
    echo "   ? Cannot test (install 'netcat' or 'telnet')"
    echo "   sudo apt-get install netcat-openbsd"
fi

# Check local listener
echo ""
echo "3. Your local listener status:"
if command -v ss &> /dev/null; then
    if ss -tuln | grep -q ":$PEER_PORT "; then
        echo "   ✓ Your app is listening on port $PEER_PORT"
    else
        echo "   ✗ Your app is NOT listening on port $PEER_PORT"
        echo "   → Start your Chat P2P app first"
    fi
elif command -v netstat &> /dev/null; then
    if netstat -tuln | grep -q ":$PEER_PORT "; then
        echo "   ✓ Your app is listening on port $PEER_PORT"
    else
        echo "   ✗ Your app is NOT listening on port $PEER_PORT"
    fi
fi

echo ""
echo "=== Summary ==="
echo "If both tests pass, you should be able to connect!"
echo "If TCP test fails, check peer's firewall and app status"

