# Tài Liệu Dự Án Chat P2P

## 📋 Tổng Quan Dự Án

**Chat P2P** là một ứng dụng chat peer-to-peer được xây dựng bằng Python và PySide6. Ứng dụng cho phép người dùng gửi tin nhắn trực tiếp với nhau qua mạng LAN hoặc localhost mà không cần server trung gian.

### Đặc Điểm Chính
- ✅ Chat peer-to-peer không cần server
- ✅ Tự động phát hiện peer trên mạng (UDP Discovery)
- ✅ Gửi/nhận tin nhắn realtime qua TCP
- ✅ Hệ thống đăng ký/đăng nhập người dùng
- ✅ Quản lý danh sách bạn bè (Friend Request/Accept/Reject)
- ✅ Lưu trữ lịch sử tin nhắn
- ✅ Giao diện hiện đại với PySide6
- ✅ Hỗ trợ emoji và file đính kèm (UI ready)

---

## 🏗️ Kiến Trúc Hệ Thống

### Mô Hình Kiến Trúc

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Login/Register│  │  Main Window  │  │  Chat Windows │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ↕
┌─────────────────────────────────────────────────────────────┐
│                      GUI Layer (PySide6)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Chat List    │  │  Chat Area    │  │ Notifications │    │
│  │   (View)      │  │   (View)      │  │   (View)      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│         ↕                 ↕                   ↕              │
│  ┌──────────────┐  ┌──────────────┐                       │
│  │ ChatList      │  │  ChatArea    │                       │
│  │ Controller    │  │  Controller  │                       │
│  └──────────────┘  └──────────────┘                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ↕
┌─────────────────────────────────────────────────────────────┐
│                    Core API Layer                            │
│                   (Core/core_api.py)                         │
│            ChatCore - High-level API                         │
│            Qt Signals for thread-safe communication         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ↕
┌─────────────────────────────────────────────────────────────┐
│                      Core Layer                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │              MessageRouter                         │       │
│  │         (Main Coordinator)                         │       │
│  └───────┬──────────────┬──────────────┬────────────┘       │
│          ↓              ↓              ↓                      │
│  ┌──────────────┐ ┌──────────┐ ┌─────────────┐           │
│  │ PeerListener  │ │ Discovery │ │ PeerClient   │           │
│  │  (TCP Server) │ │  (UDP)    │ │ (TCP Client) │           │
│  └──────────────┘ └──────────┘ └─────────────┘           │
│          ↓              ↓              ↓                      │
│  ┌──────────────┐ ┌──────────┐ ┌─────────────┐           │
│  │   DataManager │ │  Message  │ │  PeerInfo   │           │
│  │   (Storage)   │ │  (Model)  │ │   (Model)   │           │
│  └──────────────┘ └──────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                      │
                      ↕
            ┌─────────────────────┐
            │   Network Layer     │
            │  (TCP/UDP Sockets)  │
            └─────────────────────┘
```

---

## 📁 Cấu Trúc Thư Mục

```
CHAT_P2P/
│
├── main.py                          # Entry point - Khởi chạy ứng dụng
│
├── Core/                            # Core networking layer
│   ├── __init__.py
│   ├── core_api.py                  # ChatCore - High-level API cho GUI
│   │
│   ├── discovery/                   # Peer discovery module
│   │   ├── __init__.py
│   │   └── peer_discovery.py        # UDP broadcast discovery
│   │
│   ├── models/                      # Data models
│   │   ├── __init__.py
│   │   ├── message.py               # Message data structure
│   │   └── peer_info.py            # PeerInfo data structure
│   │
│   ├── networking/                  # Network communication
│   │   ├── __init__.py
│   │   ├── peer_listener.py         # TCP server (nhận tin nhắn)
│   │   └── peer_client.py           # TCP client (gửi tin nhắn)
│   │
│   ├── routing/                     # Message routing
│   │   ├── __init__.py
│   │   └── message_router.py        # Coordinator - quản lý discovery, listener, client
│   │
│   ├── storage/                     # Data persistence
│   │   ├── __init__.py
│   │   └── data_manager.py          # JSON-based storage (peers.json, messages.json)
│   │
│   └── utils/                       # Utilities
│       ├── __init__.py
│       ├── config.py                # Configuration constants
│       ├── logger.py                # Logging setup
│       └── network_mode.py          # Network mode detection (single-machine vs LAN)
│
├── Gui/                             # GUI layer (PySide6)
│   ├── assets/
│   │   ├── icons/                   # SVG icons
│   │   └── images/                  # Avatar images
│   │
│   ├── controller/                  # MVC Controllers
│   │   ├── chat_area_controller.py   # Controller cho chat area
│   │   └── chat_list_controller.py   # Controller cho chat list
│   │
│   ├── utils/                       # GUI utilities
│   │   ├── __init__.py
│   │   ├── avatar.py                # Avatar handling
│   │   └── elide_label.py           # Text elision utilities
│   │
│   └── view/                        # MVC Views
│       ├── __init__.py
│       ├── login_window.py           # Login dialog
│       ├── register_window.py        # Registration dialog
│       ├── main_window.py            # Main application window
│       ├── chat_list.py              # Chat list sidebar
│       ├── chat_area.py              # Chat message area
│       ├── chat_item.py              # Chat list item widget
│       ├── message_bubble.py         # Message bubble widget
│       ├── notifications_panel.py    # Suggestions/notifications panel
│       ├── stylesheet.py             # Main stylesheet
│       └── auth_stylesheet.py        # Auth window stylesheet
│
├── app/                             # Application layer
│   ├── __init__.py
│   ├── user_manager.py              # User authentication & management
│   └── data_migration.py            # Data migration utilities
│
├── data/                            # User data storage
│   ├── <username>/                  # Mỗi user có 1 folder
│   │   ├── profile.json             # User profile (username, display_name, peer_id, tcp_port)
│   │   ├── peers.json               # Friends list (PeerInfo objects)
│   │   └── messages.json            # Message history
│   │
│   └── ...
│
├── requirements.txt                 # Python dependencies
├── .gitignore                       # Git ignore rules
├── ARCHITECTURE.md                  # Architecture documentation (English)
├── ONE_WAY_DISCOVERY_FIX.md         # Bug fix documentation
└── PROJECT_DOCUMENTATION.md         # This file
```

---

## 🔑 Các Thành Phần Chính

### 1. Application Entry Point (`main.py`)

**Chức năng:**
- Khởi tạo QApplication
- Quản lý lifecycle của Login/Register/Main windows
- Phân bổ TCP port cho mỗi user
- Điều hướng giữa các windows

**Luồng hoạt động:**
1. Hiển thị LoginWindow
2. Nếu đăng ký → hiển thị RegisterWindow
3. Sau khi đăng nhập thành công → tạo MainWindow với ChatCore
4. Lưu TCP port vào profile.json để tái sử dụng

---

### 2. Core API Layer (`Core/core_api.py`)

**ChatCore Class:**
- **Mục đích:** Cung cấp high-level API cho GUI layer
- **Thread-safe:** Sử dụng Qt Signals để giao tiếp giữa background threads và main thread

**Key Methods:**
```python
start()                          # Khởi động ChatCore (discovery + listener)
stop()                           # Dừng ChatCore
send_message(peer_id, content)  # Gửi tin nhắn
get_known_peers()                # Lấy danh sách bạn bè
get_message_history(peer_id)    # Lấy lịch sử tin nhắn
send_friend_request(peer_id)    # Gửi friend request
accept_friend(peer_id)           # Chấp nhận friend request
reject_friend(peer_id)           # Từ chối friend request
```

**Qt Signals:**
- `signals.message_received` - Tin nhắn mới nhận được
- `signals.peer_updated` - Peer (bạn bè) được cập nhật
- `signals.temp_peer_updated` - Peer mới được phát hiện (chưa là bạn)
- `signals.temp_peer_removed` - Peer bị xóa khỏi suggestions
- `signals.friend_request_received` - Nhận friend request
- `signals.friend_accepted` - Friend request được chấp nhận
- `signals.friend_rejected` - Friend request bị từ chối

---

### 3. Message Router (`Core/routing/message_router.py`)

**Mục đích:** Coordinator chính, quản lý tất cả các component:
- PeerListener (TCP server)
- PeerDiscovery (UDP discovery)
- PeerClient (TCP client)
- DataManager (storage)

**Chức năng chính:**
1. **Khởi tạo:**
   - Tạo peer_id (UUID)
   - Load profile.json để lấy tcp_port đã lưu
   - Khởi động PeerListener TRƯỚC (quan trọng!)
   - Khởi động PeerDiscovery
   - Load peers.json vào memory

2. **Quản lý Peers:**
   - `_peers`: Dict chứa bạn bè đã chấp nhận (từ peers.json)
   - `temp_discovered_peers`: Dict chứa peer mới phát hiện (chưa là bạn)
   - `_outgoing_requests`: Set peer_id đã gửi friend request
   - `_incoming_requests`: Set peer_id đã nhận friend request
   - `_pending_friend_accepts`: Dict peer_id -> timestamp (chờ discovery cung cấp tcp_port)

3. **Xử lý tin nhắn:**
   - `_handle_incoming_message()`: Xử lý tin nhắn từ PeerListener
   - Phân loại: TEXT, FRIEND_REQUEST, FRIEND_ACCEPT, FRIEND_REJECT, FRIEND_SYNC
   - Lưu tin nhắn vào messages.json
   - Gọi callback để GUI cập nhật

4. **Discovery handling:**
   - `_handle_peer_discovered()`: Xử lý peer mới được phát hiện
   - Cập nhật IP/tcp_port cho bạn bè hiện có
   - Thêm vào temp_discovered_peers nếu chưa là bạn
   - Hoàn thành pending friend accepts

5. **Gửi tin nhắn:**
   - `send_message()`: Validate peer, tạo Message object, gửi qua PeerClient
   - Validate tcp_port (phải trong khoảng 55000-55199)
   - Track send failures, đánh dấu offline sau 3 lần fail

---

### 4. Peer Discovery (`Core/discovery/peer_discovery.py`)

**Mục đích:** Phát hiện peer khác trên mạng qua UDP broadcast

**Cơ chế hoạt động:**
1. **Broadcast Loop (Thread):**
   - Mỗi 1 giây gửi UDP broadcast packet chứa:
     - `peer_id`
     - `display_name`
     - `tcp_port` (QUAN TRỌNG!)
   - Broadcast đến `255.255.255.255:50555` (LAN mode) hoặc `127.0.0.1:50555` (single-machine mode)

2. **Listen Loop (Thread):**
   - Lắng nghe UDP packet trên port 50555
   - Parse JSON packet
   - Validate tcp_port (55000-55199)
   - Tạo PeerInfo object
   - Gọi `on_peer_found()` callback

**Network Mode Detection:**
- **Single-machine mode:** Nếu phát hiện nhiều instance đang chạy hoặc chỉ có virtual adapters
- **LAN mode:** Nếu có valid LAN IP (192.168.x.x, 10.x.x.x, 172.16-31.x.x)

---

### 5. Peer Listener (`Core/networking/peer_listener.py`)

**Mục đích:** TCP server nhận tin nhắn từ peer khác

**Cơ chế hoạt động:**
1. **Start:**
   - Bind socket đến `0.0.0.0:<tcp_port>` (mặc định 55000)
   - Listen với backlog=5
   - Trả về actual port (nếu port bị chiếm, OS sẽ chọn port khác)

2. **Accept Loop (Thread):**
   - Chấp nhận kết nối mới
   - Mỗi connection được xử lý trong thread riêng

3. **Client Handler (Thread per connection):**
   - Nhận data từ socket (buffer 4096 bytes)
   - Parse newline-delimited JSON messages
   - Tạo Message object từ JSON
   - Gọi `on_message()` callback với message và sender IP/port

**Message Format:**
```
[Message JSON]\n[Message JSON]\n[Message JSON]\n
```

---

### 6. Peer Client (`Core/networking/peer_client.py`)

**Mục đích:** TCP client gửi tin nhắn đến peer khác

**Cơ chế hoạt động:**
- Tạo socket mới cho mỗi lần gửi
- Connect đến `peer_ip:peer_tcp_port`
- Gửi `message.to_json() + "\n"`
- Đóng socket sau khi gửi xong

**Lưu ý:** Mỗi lần gửi tạo connection mới (không persistent connection)

---

### 7. Data Manager (`Core/storage/data_manager.py`)

**Mục đích:** Quản lý lưu trữ dữ liệu dạng JSON

**Cấu trúc dữ liệu:**
```
data/<username>/
├── profile.json      # User profile
├── peers.json         # Friends list (Dict[peer_id, PeerInfo])
├── messages.json      # Message history (List[Message])
└── settings.json      # Settings (chưa sử dụng)
```

**Thread-safe:** Sử dụng `threading.RLock()` để đảm bảo thread-safe

**Key Methods:**
- `load_profile()` / `save_profile()`
- `load_peers()` / `save_peers()` / `update_peer()` / `remove_peer()`
- `load_messages()` / `append_message()`

**Validation:**
- Filter peers với tcp_port không hợp lệ (< 55000 hoặc > 55199)
- Không lưu peer với tcp_port = 0

---

### 8. User Manager (`app/user_manager.py`)

**Mục đích:** Quản lý đăng ký/đăng nhập người dùng

**Chức năng:**
- `register(username, password, display_name)`: Đăng ký user mới
- `login(username, password)`: Xác thực và trả về User object
- `get_user(username)`: Lấy thông tin user

**Lưu trữ:**
- User data lưu trong `data/<normalized_username>/profile.json`
- Password được hash bằng SHA256
- Username được normalize (lowercase, thay @ thành _at_)

**User Model:**
```python
@dataclass
class User:
    username: str              # Email
    password_hash: str          # SHA256 hash
    display_name: str           # Tên hiển thị
    avatar_path: Optional[str] # Đường dẫn avatar
    user_id: str               # UUID ngắn (8 ký tự)
```

---

### 9. GUI Components

#### 9.1. Main Window (`Gui/view/main_window.py`)

**Layout:**
- **Left (25%):** ChatList - Danh sách cuộc trò chuyện
- **Center (50%):** ChatArea - Khu vực chat
- **Right (25%):** NotificationsPanel - Suggestions và notifications

**Chức năng:**
- Khởi tạo ChatCore
- Kết nối Qt Signals từ ChatCore
- Quản lý peer list và unread counts
- Xử lý friend requests (popup dialog)
- Refresh peer list mỗi 5 giây
- Cleanup offline peers mỗi 5 phút

**Key Methods:**
- `_on_message_received_signal()`: Xử lý tin nhắn mới
- `_on_peer_updated_signal()`: Cập nhật peer
- `_on_friend_request_received_signal()`: Hiển thị dialog friend request
- `_send_message_from_controller()`: Gửi tin nhắn qua ChatCore

#### 9.2. Chat List (`Gui/view/chat_list.py`)

**Chức năng:**
- Hiển thị danh sách cuộc trò chuyện
- Search functionality
- Tabs: DIRECT, GROUPS, PUBLIC (chưa implement groups/public)
- Unread count badges
- Online/offline status

#### 9.3. Chat Area (`Gui/view/chat_area.py`)

**Chức năng:**
- Hiển thị tin nhắn (message bubbles)
- Input field với emoji picker
- File attachment button
- Send button
- Load chat history khi chọn peer

#### 9.4. Notifications Panel (`Gui/view/notifications_panel.py`)

**Chức năng:**
- Hiển thị Suggestions (temp discovered peers)
- "Add" button để gửi friend request
- Click vào suggestion để mở chat (nếu đã là bạn)

---

## 🔄 Luồng Dữ Liệu (Data Flow)

### 1. Luồng Gửi Tin Nhắn

```
User nhập tin nhắn
    ↓
ChatAreaController._send_message()
    ↓
MainWindow._send_message_from_controller()
    ↓
ChatCore.send_message(peer_id, content)
    ↓
MessageRouter.send_message()
    ↓
Message.create() - Tạo Message object
    ↓
PeerClient.send(peer_ip, peer_tcp_port, message)
    ↓
TCP socket.sendall() - Gửi JSON qua TCP
    ↓
Network transmission
```

### 2. Luồng Nhận Tin Nhắn

```
TCP socket nhận data
    ↓
PeerListener._handle_client() - Parse newline-delimited JSON
    ↓
Message.from_json() - Tạo Message object
    ↓
PeerListener.on_message() callback
    ↓
MessageRouter._handle_incoming_message()
    ↓
DataManager.append_message() - Lưu vào messages.json
    ↓
MessageRouter._on_message_callback()
    ↓
ChatCore._handle_router_message()
    ↓
ChatCore.signals.message_received.emit() - Qt Signal
    ↓
MainWindow._on_message_received_signal() - Main thread
    ↓
ChatArea.add_message() - Cập nhật UI
```

### 3. Luồng Peer Discovery

```
Peer A khởi động
    ↓
PeerDiscovery.start() - Khởi động broadcast + listen threads
    ↓
Broadcast loop: Gửi UDP packet mỗi 1 giây
    ↓
Peer B nhận UDP packet
    ↓
PeerDiscovery._listen_loop() - Parse packet
    ↓
Tạo PeerInfo với tcp_port từ packet
    ↓
PeerDiscovery.on_peer_found() callback
    ↓
MessageRouter._handle_peer_discovered()
    ↓
Kiểm tra:
  - Nếu là bạn → Cập nhật IP/tcp_port
  - Nếu chưa là bạn → Thêm vào temp_discovered_peers
  - Nếu có pending accept → Hoàn thành accept
    ↓
ChatCore.signals.temp_peer_updated.emit() - Qt Signal
    ↓
MainWindow._on_temp_peer_updated_signal()
    ↓
NotificationsPanel.load_suggestions() - Hiển thị trong Suggestions
```

### 4. Luồng Friend Request

```
User click "Add" trên suggestion
    ↓
MainWindow._on_suggestion_add_requested()
    ↓
ChatCore.send_friend_request(peer_id)
    ↓
MessageRouter.send_friend_request()
    ↓
Message.create_friend_request()
    ↓
PeerClient.send() - Gửi FRIEND_REQUEST message
    ↓
Peer B nhận FRIEND_REQUEST
    ↓
MessageRouter._handle_incoming_message() - msg_type == "FRIEND_REQUEST"
    ↓
Thêm vào _incoming_requests
    ↓
Tạo temporary peer entry nếu chưa có
    ↓
ChatCore.signals.friend_request_received.emit()
    ↓
MainWindow._on_friend_request_received_signal()
    ↓
Hiển thị dialog "Accept/Reject"
    ↓
User click "Accept"
    ↓
ChatCore.accept_friend(peer_id)
    ↓
MessageRouter.send_friend_accept()
    ↓
Gửi FRIEND_ACCEPT message
    ↓
Gửi FRIEND_SYNC message (đảm bảo mutual friendship)
    ↓
Lưu peer vào peers.json
    ↓
ChatCore.signals.friend_accepted.emit()
    ↓
MainWindow cập nhật UI - Peer xuất hiện trong chat list
```

---

## ⚙️ Cấu Hình (Configuration)

### Network Configuration (`Core/utils/config.py`)

```python
# UDP Discovery
UDP_DISCOVERY_PORT = 50555           # Port cho UDP broadcast
UDP_DISCOVERY_INTERVAL = 1.0         # Giây giữa các lần broadcast
UDP_DISCOVERY_TIMEOUT = 1.0          # Socket timeout khi listen

# TCP Communication
TCP_BASE_PORT = 55000                # Port mặc định cho TCP listener
TCP_CONNECT_TIMEOUT = 5.0             # Timeout khi connect TCP
BUFFER_SIZE = 4096                   # Kích thước buffer khi nhận data

# Storage
PROFILE_FILENAME = "profile.json"
PEERS_FILENAME = "peers.json"
MESSAGES_FILENAME = "messages.json"
SETTINGS_FILENAME = "settings.json"
```

### Port Range

- **TCP Port:** 55000-55199 (200 ports)
- **UDP Port:** 50555 (cố định)

**Lưu ý:** TCP port được lưu trong profile.json để tái sử dụng giữa các lần khởi động.

---

## 🎯 Tính Năng

### ✅ Đã Implement

1. **Authentication:**
   - Đăng ký user mới (email + password + display name)
   - Đăng nhập với email/password
   - Lưu user profile

2. **Peer Discovery:**
   - Tự động phát hiện peer trên mạng (UDP broadcast)
   - Hỗ trợ single-machine mode (localhost) và LAN mode
   - Filter virtual adapters (VMware, VirtualBox)

3. **Friend Management:**
   - Gửi friend request
   - Chấp nhận/từ chối friend request
   - FRIEND_SYNC để đảm bảo mutual friendship
   - Suggestions list (temp discovered peers)

4. **Messaging:**
   - Gửi/nhận tin nhắn text realtime
   - Lưu lịch sử tin nhắn
   - Hiển thị timestamp
   - Unread count

5. **UI Features:**
   - Modern UI với PySide6
   - Chat list với search
   - Message bubbles
   - Emoji picker
   - File attachment button (UI ready, chưa implement backend)

### 🚧 Chưa Implement / TODO

1. **File Transfer:**
   - UI đã có button, nhưng chưa implement backend
   - Cần implement FILE message type và chunking

2. **Group Chat:**
   - UI có tab GROUPS nhưng chưa implement
   - Cần implement group management trong Core

3. **Voice/Video Call:**
   - UI có button nhưng chưa implement
   - Cần integrate media libraries

4. **Encryption:**
   - Hiện tại tin nhắn gửi plaintext
   - Nên implement TLS/SSL hoặc end-to-end encryption

5. **Offline Messages:**
   - Hiện tại chỉ gửi được khi peer online
   - Cần implement message queue cho offline delivery

---

## 🚀 Cách Chạy Ứng Dụng

### 1. Cài Đặt Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `PySide6>=6.5.0` - GUI framework

**Optional:**
- `psutil` - Để detect network mode tốt hơn (fallback nếu không có)

### 2. Chạy Ứng Dụng

```bash
python main.py
```

### 3. Test Trên Cùng Máy (Single-Machine Mode)

```bash
# Terminal 1
python main.py  # User 1

# Terminal 2
python main.py  # User 2
```

Ứng dụng sẽ tự động detect multiple instances và sử dụng `127.0.0.1` cho communication.

### 4. Test Trên Mạng LAN

1. Đảm bảo cả 2 máy cùng mạng LAN
2. Chạy ứng dụng trên mỗi máy
3. Ứng dụng sẽ tự động detect LAN mode và sử dụng LAN IP
4. Peers sẽ tự động phát hiện nhau qua UDP discovery

### 5. Firewall Configuration

Nếu firewall chặn, cần mở ports:
- **UDP 50555** - Cho discovery
- **TCP 55000-55199** - Cho messaging (hoặc port cụ thể của user)

---

## 🔧 Technical Details

### Threading Model

**Main Thread:**
- Qt GUI event loop
- Signal/Slot handling
- User interactions

**Background Threads:**
- **PeerListener Thread:** Accept incoming connections
- **Client Handler Threads:** Mỗi connection có 1 thread để nhận messages
- **Discovery Broadcast Thread:** Gửi UDP broadcast định kỳ
- **Discovery Listen Thread:** Lắng nghe UDP packets

**Thread Safety:**
- Sử dụng `threading.RLock()` trong MessageRouter và DataManager
- Qt Signals tự động queue messages từ background threads đến main thread
- Không có direct GUI calls từ background threads

### Message Protocol

**Message Structure:**
```json
{
  "message_id": "uuid",
  "sender_id": "peer_id",
  "sender_name": "display_name",
  "receiver_id": "peer_id",
  "content": "message text",
  "timestamp": 1234567890.123,
  "msg_type": "text" | "FRIEND_REQUEST" | "FRIEND_ACCEPT" | "FRIEND_REJECT" | "FRIEND_SYNC"
}
```

**Message Types:**
- `text`: Tin nhắn text thông thường
- `FRIEND_REQUEST`: Yêu cầu kết bạn
- `FRIEND_ACCEPT`: Chấp nhận kết bạn
- `FRIEND_REJECT`: Từ chối kết bạn
- `FRIEND_SYNC`: Đồng bộ thông tin peer (đảm bảo mutual friendship)

**Transmission:**
- Messages được serialize thành JSON
- Gửi qua TCP với newline delimiter (`\n`)
- Cho phép streaming multiple messages trong 1 connection

### Data Storage Format

**profile.json:**
```json
{
  "username": "user@example.com",
  "display_name": "User Name",
  "peer_id": "uuid",
  "tcp_port": 55000,
  "password_hash": "sha256_hash",
  "user_id": "short_uuid",
  "avatar_path": "path/to/avatar.jpg"
}
```

**peers.json:**
```json
{
  "peer_id_1": {
    "peer_id": "uuid",
    "display_name": "Friend Name",
    "ip": "192.168.1.100",
    "tcp_port": 55001,
    "last_seen": 1234567890.123,
    "status": "online"
  },
  "peer_id_2": { ... }
}
```

**messages.json:**
```json
[
  {
    "message_id": "uuid",
    "sender_id": "peer_id",
    "sender_name": "Sender Name",
    "receiver_id": "peer_id",
    "content": "Message text",
    "timestamp": 1234567890.123,
    "msg_type": "text"
  },
  ...
]
```

### Network Mode Detection

**Single-Machine Mode:**
- Trigger khi:
  - Phát hiện nhiều instance đang chạy
  - Chỉ có virtual adapters (VMware, VirtualBox)
  - Không có valid LAN IP
- Sử dụng `127.0.0.1` cho tất cả communication

**LAN Mode:**
- Trigger khi:
  - Có valid LAN IP (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
  - Không phát hiện multiple instances
- Sử dụng LAN IP cho communication
- Broadcast đến `255.255.255.255`

### Error Handling

**Network Errors:**
- Connection refused → Mark peer as offline sau 3 lần fail
- Timeout → Retry hoặc mark offline
- Invalid port → Remove peer khỏi friends list

**Data Errors:**
- Invalid JSON → Skip message, log warning
- Missing fields → Use defaults, log warning
- Invalid tcp_port → Filter out peer, không load/save

**Thread Safety:**
- Tất cả callbacks được wrap trong try-except
- Không crash thread nếu callback có lỗi
- Log errors với full traceback

---

## 🐛 Known Issues & Fixes

### One-Way Discovery Fix

**Vấn đề:** Discovery chỉ hoạt động một chiều trong một số trường hợp.

**Giải pháp:** Đã fix trong `ONE_WAY_DISCOVERY_FIX.md`:
1. Giảm discovery interval từ 3.0s xuống 1.0s
2. Xử lý FRIEND_REQUEST/FRIEND_ACCEPT khi peer chưa được discover
3. Pending friend accepts được hoàn thành tự động khi discovery cung cấp tcp_port
4. Filter peers với tcp_port=0 khi load peers.json
5. Discovery luôn notify router (kể cả cho friends) để cập nhật port

---

## 📝 Development Notes

### Code Style
- Sử dụng type hints (Python 3.7+)
- Docstrings cho classes và methods
- Logging với `logging` module
- Thread-safe với locks và Qt Signals

### Best Practices
- Separation of concerns: Core layer độc lập với GUI
- Thread-safe communication: Chỉ dùng Qt Signals từ background threads
- Error handling: Wrap callbacks trong try-except
- Data validation: Validate tcp_port, IP, message format
- Resource cleanup: Close sockets, stop threads khi shutdown

### Future Improvements
1. **Encryption:** Implement TLS/SSL cho TCP connections
2. **File Transfer:** Implement FILE message type với chunking
3. **Group Chat:** Implement group management
4. **Offline Queue:** Queue messages khi peer offline
5. **NAT Traversal:** STUN/TURN để hỗ trợ internet-wide P2P
6. **Database:** Migrate từ JSON sang SQLite cho performance tốt hơn
7. **Mobile App:** Cross-platform với React Native hoặc Flutter

---

## 📚 References

- **PySide6 Documentation:** https://doc.qt.io/qtforpython/
- **Python Socket Programming:** https://docs.python.org/3/library/socket.html
- **P2P Architecture Patterns:** Various academic papers

---

## 📄 License

[Chưa có license - cần thêm]

---

**Document Version:** 1.0  
**Last Updated:** 2024  
**Maintainer:** [Your Name]

---

## 📞 Contact & Support

[Thêm thông tin liên hệ nếu cần]

