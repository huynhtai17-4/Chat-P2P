import os

# UDP discovery removed - only TCP communication now

TCP_BASE_PORT = 55000             # default TCP listening port, can be overridden
TCP_CONNECT_TIMEOUT = 5.0         # seconds for TCP connect attempts
BUFFER_SIZE = 4096                # bytes per socket recv iteration

DATA_ROOT = os.path.join(os.getcwd(), "Data")
PROFILE_FILENAME = "profile.json"
PEERS_FILENAME = "peers.json"
MESSAGES_FILENAME = "messages.json"
SETTINGS_FILENAME = "settings.json"

MESSAGE_PACKET_TYPE = "MESSAGE"
