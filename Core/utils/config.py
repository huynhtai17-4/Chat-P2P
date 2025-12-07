import os

UDP_DISCOVERY_PORT = 50555        # UDP broadcast listening port
UDP_DISCOVERY_INTERVAL = 10.0     # seconds between broadcast beacons (optimized: reduced frequency to save resources)
UDP_DISCOVERY_TIMEOUT = 2.0       # socket timeout when listening for peers (increased to match interval)
UDP_BROADCAST_ADDR = "255.255.255.255"

TCP_BASE_PORT = 55000             # default TCP listening port, can be overridden
TCP_CONNECT_TIMEOUT = 5.0         # seconds for TCP connect attempts
BUFFER_SIZE = 4096                # bytes per socket recv iteration

DATA_ROOT = os.path.join(os.getcwd(), "Data")
PROFILE_FILENAME = "profile.json"
PEERS_FILENAME = "peers.json"
MESSAGES_FILENAME = "messages.json"
SETTINGS_FILENAME = "settings.json"

DISCOVERY_PACKET_TYPE = "DISCOVER"
MESSAGE_PACKET_TYPE = "MESSAGE"
