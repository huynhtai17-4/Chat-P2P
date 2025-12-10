import os

TCP_BASE_PORT = 55000
TCP_CONNECT_TIMEOUT = 5.0
BUFFER_SIZE = 4096

DATA_ROOT = os.path.join(os.getcwd(), "Data")
PROFILE_FILENAME = "profile.json"
PEERS_FILENAME = "peers.json"
MESSAGES_FILENAME = "messages.json"
SETTINGS_FILENAME = "settings.json"

MESSAGE_PACKET_TYPE = "MESSAGE"
