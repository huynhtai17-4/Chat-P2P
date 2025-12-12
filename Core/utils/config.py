import os

TCP_BASE_PORT = 55000 # Port mặc định cho TCP server
TCP_CONNECT_TIMEOUT = 5.0 # Thời gian chờ kết nối TCP
BUFFER_SIZE = 4096 # Kích thước bộ đệm

DATA_ROOT = os.path.join(os.getcwd(), "Data") # Thư mục lưu trữ dữ liệu
PROFILE_FILENAME = "profile.json" # Tên file lưu trữ thông tin người dùng
PEERS_FILENAME = "peers.json" # Tên file lưu trữ danh sách peers
MESSAGES_FILENAME = "messages.json" # Tên file lưu trữ tin nhắn
SETTINGS_FILENAME = "settings.json" # Tên file lưu trữ cấu hình

MESSAGE_PACKET_TYPE = "MESSAGE" # Kiểu gói tin tin nhắn
