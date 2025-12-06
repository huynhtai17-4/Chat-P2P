"""
Central place for configuration constants used by the Core package.
Modify these values to adapt the networking behaviour to your LAN.
"""

import os

# -----------------------------
# Networking
# -----------------------------
UDP_DISCOVERY_PORT = 50555        # UDP broadcast listening port
UDP_DISCOVERY_INTERVAL = 1.0      # seconds between broadcast beacons (reduced for faster discovery)
UDP_DISCOVERY_TIMEOUT = 1.0       # socket timeout when listening for peers
UDP_BROADCAST_ADDR = "255.255.255.255"

TCP_BASE_PORT = 55000             # default TCP listening port, can be overridden
TCP_CONNECT_TIMEOUT = 5.0         # seconds for TCP connect attempts
BUFFER_SIZE = 4096                # bytes per socket recv iteration

# -----------------------------
# Storage / files
# -----------------------------
DATA_ROOT = os.path.join(os.getcwd(), "Data")
PROFILE_FILENAME = "profile.json"
PEERS_FILENAME = "peers.json"
MESSAGES_FILENAME = "messages.json"
SETTINGS_FILENAME = "settings.json"

# -----------------------------
# Misc
# -----------------------------
DISCOVERY_PACKET_TYPE = "DISCOVER"
MESSAGE_PACKET_TYPE = "MESSAGE"

