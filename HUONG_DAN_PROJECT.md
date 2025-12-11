# 📚 HƯỚNG DẪN CHI TIẾT PROJECT CHAT P2P

## 🎯 TỔNG QUAN Dự ÁN

Đây là ứng dụng **Chat P2P (Peer-to-Peer)** được xây dựng bằng Python và PySide6 (Qt). Ứng dụng cho phép người dùng:
- Đăng ký và đăng nhập tài khoản
- Kết nối trực tiếp với người dùng khác qua mạng LAN
- Nhắn tin văn bản, gửi file, gửi ảnh
- Gọi video/audio call
- Quản lý danh sách bạn bè

**Đặc điểm:** Không cần máy chủ trung tâm, các thiết bị kết nối trực tiếp với nhau.

---

## 📁 CẤU TRÚC THƯ MỤC

```
CHAT_P2P/
├── main.py                          # File khởi chạy chính
├── app/                             # Quản lý người dùng
│   └── user_manager.py              # Đăng ký/đăng nhập
├── Core/                            # Lõi xử lý logic
│   ├── core_api.py                  # API chính giao tiếp với GUI
│   ├── call/                        # Xử lý cuộc gọi
│   │   └── call_manager.py          # Quản lý video/audio call
│   ├── media/                       # Xử lý âm thanh/video
│   │   ├── audio_stream.py          # Thu/phát âm thanh
│   │   └── video_stream.py          # Thu/phát video
│   ├── models/                      # Các model dữ liệu
│   │   ├── message.py               # Cấu trúc tin nhắn
│   │   └── peer_info.py             # Thông tin người dùng
│   ├── networking/                  # Xử lý mạng
│   │   ├── peer_client.py           # Gửi tin nhắn TCP
│   │   ├── peer_listener.py         # Lắng nghe kết nối TCP
│   │   └── udp_stream.py            # Gửi/nhận UDP (call)
│   ├── routing/                     # Định tuyến tin nhắn
│   │   ├── message_router.py        # Router chính
│   │   ├── message_handlers.py      # Xử lý tin nhắn đến
│   │   ├── peer_manager.py          # Quản lý danh sách peer
│   │   ├── friend_request_manager.py# Quản lý lời mời kết bạn
│   │   └── status_broadcaster.py    # Phát trạng thái online
│   ├── storage/                     # Lưu trữ dữ liệu
│   │   ├── data_manager.py          # Quản lý file/folder
│   │   └── peer_message_storage.py  # Lưu tin nhắn
│   └── utils/                       # Tiện ích
│       ├── config.py                # Cấu hình (port, timeout)
│       └── network_mode.py          # Xác định IP mạng
├── Gui/                             # Giao diện người dùng
│   ├── view/                        # Các màn hình
│   │   ├── auth_stylesheet.py       # CSS đăng nhập/đăng ký
│   │   ├── stylesheet.py            # CSS chính
│   │   ├── login_window.py          # Màn hình đăng nhập
│   │   ├── register_window.py       # Màn hình đăng ký
│   │   ├── main_window.py           # Màn hình chính
│   │   ├── chat_area.py             # Khu vực chat
│   │   ├── chat_list.py             # Danh sách hội thoại
│   │   ├── chat_item.py             # Item trong danh sách
│   │   ├── message_bubble.py        # Bong bóng tin nhắn
│   │   ├── call_dialog.py           # Dialog cuộc gọi đến
│   │   ├── call_window.py           # Cửa sổ video call
│   │   └── notifications_panel.py   # Panel thông báo
│   ├── controller/                  # Điều khiển logic GUI
│   │   ├── main_window_controller.py# Controller màn hình chính
│   │   ├── chat_area_controller.py  # Controller khu vực chat
│   │   └── chat_list_controller.py  # Controller danh sách chat
│   └── utils/                       # Tiện ích GUI
│       ├── avatar.py                # Xử lý ảnh đại diện
│       └── elide_label.py           # Label rút gọn văn bản
└── data/                            # Dữ liệu người dùng (tự tạo khi chạy)
    └── [email]_at_[domain]/
        ├── profile.json             # Thông tin cá nhân
        ├── peers.json               # Danh sách bạn bè
        └── chats/                   # Tin nhắn từng người
```

---

## 🔄 LUỒNG HOẠT ĐỘNG TỔNG QUÁT

### 1. **Khởi động ứng dụng** (`main.py`)
```
User chạy main.py 
    → Tạo ChatApplication
    → Hiển thị LoginWindow
    → Sau khi đăng nhập thành công
    → Mở MainWindow với Core API
```

### 2. **Đăng nhập/Đăng ký** (`app/user_manager.py`)
```
Nhập email + password
    → UserManager kiểm tra trong data/
    → Nếu đúng: Trả về User object
    → MainWindow khởi tạo ChatCore
```

### 3. **Kết nối P2P** (`Core/routing/message_router.py`)
```
ChatCore.start()
    → Khởi động PeerListener (lắng nghe TCP)
    → Khởi động StatusBroadcaster (phát UDP)
    → Tải danh sách peers từ peers.json
    → Gửi STATUS_UPDATE đến tất cả peers
    → Peers nhận được sẽ cập nhật trạng thái "online"
```

### 4. **Gửi tin nhắn** (`Core/models/message.py`)
```
User gõ tin nhắn → Click Send
    → Controller gọi chat_core.send_message()
    → Tạo Message object
    → PeerClient gửi qua TCP đến IP:Port của peer
    → Lưu vào peer_message_storage
    → Hiển thị trong chat_area
```

### 5. **Nhận tin nhắn** (`Core/networking/peer_listener.py`)
```
PeerListener nhận kết nối TCP
    → Đọc JSON message
    → MessageHandlers xử lý theo msg_type
    → Phát signal message_received
    → Controller nhận signal
    → Hiển thị bubble trong chat
```

### 6. **Video Call** (`Core/call/call_manager.py`)
```
User click nút video call
    → ChatCore.start_call()
    → CallManager khởi động camera + mic
    → Gửi CALL_REQUEST qua TCP
    → Peer nhận được → hiện CallDialog
    → Peer accept → gửi CALL_ACCEPT
    → Cả 2 bên khởi động UDP stream
    → Video/Audio được truyền qua UDP
```

---

## 📄 CHI TIẾT TỪNG FILE

---

## 🎬 `main.py` - FILE KHỞI CHẠY CHÍNH

### Mục đích
File entry point của ứng dụng, quản lý luồng màn hình login → register → main window.

### Class: `ChatApplication`

#### `__init__(self)`
- Khởi tạo QApplication (framework Qt)
- Load stylesheet từ `STYLESHEET + AUTH_STYLESHEET`
- Tạo UserManager để quản lý tài khoản
- Khởi tạo biến theo dõi user hiện tại

#### `run(self)` → int
- Hiển thị màn hình login
- Chạy event loop Qt
- **Return:** Mã thoát ứng dụng

#### `show_login(self)`
- Tạo và hiển thị LoginWindow
- Kết nối signal login_successful → `on_login_success()`
- Kết nối signal register_requested → chuyển sang RegisterWindow

#### `show_register(self)`
- Tạo và hiển thị RegisterWindow
- Kết nối signal registration_successful → quay lại LoginWindow

#### `on_login_success(self, user: User)`
- Lưu user đã đăng nhập vào `self.current_user`
- Đóng LoginWindow
- Gọi `show_main_window()`

#### `on_register_success(self, username: str, display_name: str)`
- Sau khi đăng ký thành công
- Tự động mở LoginWindow với username đã điền sẵn

#### `show_main_window(self)`
- Đọc `tcp_port` từ profile.json (nếu có)
- Nếu chưa có port → gọi `_allocate_tcp_port()` để cấp phát
- Tạo MainWindow với thông tin user và tcp_port
- Hiển thị cửa sổ chính

#### `_allocate_tcp_port(self, base=55000, max_ports=200)` → int
- Tìm port TCP khả dụng từ 55000-55200
- Thử bind socket để kiểm tra port trống
- **Return:** Port khả dụng hoặc 0 nếu không tìm được

---

## 👤 `app/user_manager.py` - QUẢN LÝ NGƯỜI DÙNG

### Hàm tiện ích

#### `_hash_password(password: str)` → str
- Mã hóa mật khẩu bằng SHA256
- **Return:** Chuỗi hash hex

#### `_normalize_username(username: str)` → str
- Chuẩn hóa email thành tên thư mục hợp lệ
- VD: `user@gmail.com` → `user_at_gmail.com`
- Thay ký tự đặc biệt bằng `_`

### Class: `User` (dataclass)

Lưu trữ thông tin người dùng.

**Thuộc tính:**
- `username: str` - Email đăng nhập
- `password_hash: str` - Mật khẩu đã hash
- `display_name: str` - Tên hiển thị
- `avatar_path: Optional[str]` - Đường dẫn ảnh đại diện
- `user_id: Optional[str]` - ID duy nhất (8 ký tự)

#### `get_folder_name(self)` → str
- Trả về tên thư mục lưu dữ liệu của user
- Sử dụng `_normalize_username()`

#### `to_dict(self)` → Dict
- Chuyển User thành dictionary
- Dùng để lưu vào JSON

#### `from_dict(cls, data: Dict)` → User
- Tạo User object từ dictionary
- Dùng để đọc từ JSON

### Class: `UserManager`

Quản lý đăng ký và đăng nhập.

#### `__init__(self)`
- Tạo dict lưu trữ users: `{username_lowercase: User}`
- Gọi `_load_users()` để tải tất cả user từ thư mục data/

#### `_load_users(self)`
- Duyệt tất cả thư mục trong `data/`
- Đọc file `profile.json` trong mỗi thư mục
- Load vào `self.users`

#### `_save_user(self, user: User, folder_name: Optional[str])`
- Tạo thư mục `data/[folder_name]/`
- Lưu thông tin user vào `profile.json`

#### `register(self, username, password, display_name, avatar_path)` → (bool, str)
- Kiểm tra email hợp lệ (regex pattern)
- Kiểm tra email đã tồn tại chưa
- Kiểm tra display_name đã tồn tại chưa
- Tạo user_id ngẫu nhiên (8 ký tự từ UUID)
- Lưu user mới
- **Return:** (True, "Success") hoặc (False, "Error message")

#### `login(self, username, password)` → (bool, Optional[User], str)
- Tìm user theo username (không phân biệt hoa thường)
- So sánh password_hash
- **Return:** (True, User, "Success") hoặc (False, None, "Error")

#### `get_user(self, username: str)` → Optional[User]
- Lấy User object từ username
- **Return:** User hoặc None

---

## 🧠 `Core/core_api.py` - API GIAO TIẾP GIỮA GUI VÀ CORE

### Class: `CoreSignals` (QObject)

Các Qt Signal để gửi sự kiện từ Core lên GUI.

**Signals:**
- `message_received = Signal(dict)` - Nhận tin nhắn mới
- `peer_updated = Signal(dict)` - Peer thay đổi trạng thái
- `friend_request_received = Signal(str, str)` - Nhận lời mời kết bạn
- `friend_accepted = Signal(str)` - Lời mời được chấp nhận
- `friend_rejected = Signal(str)` - Lời mời bị từ chối
- `call_request_received = Signal(str, str, str)` - Cuộc gọi đến
- `call_accepted = Signal(str)` - Cuộc gọi được chấp nhận
- `call_rejected = Signal(str)` - Cuộc gọi bị từ chối
- `call_ended = Signal(str)` - Cuộc gọi kết thúc
- `remote_video_frame = Signal(bytes)` - Frame video từ peer

### Class: `ChatCore`

Lớp API chính, giao tiếp giữa GUI Controller và các module Core.

#### `__init__(self, username, display_name, tcp_port)`
- Lưu thông tin user
- Tạo `CoreSignals` để phát sự kiện
- Khởi tạo `MessageRouter` - lõi xử lý P2P
- Khởi tạo `CallManager` - quản lý video/audio call
- Kết nối callbacks từ CallManager

#### `start(self)`
- Kết nối callback handlers với router
- Gọi `router.connect_core()` để:
  - Khởi động PeerListener (lắng nghe TCP)
  - Khởi động StatusBroadcaster (phát UDP status)
  - Tải danh sách peers
- Lấy local IP từ `network_mode.get_local_ip()`
- Gửi trạng thái online đến tất cả peers

#### `stop(self)`
- Dừng router và tất cả kết nối

#### `send_message(self, peer_id, content, msg_type, file_name, file_data, audio_data)` → bool
- Gọi `router.send_message()` để gửi tin nhắn
- Nếu thành công → emit signal `message_received`
- **Return:** True nếu gửi thành công

#### `get_known_peers(self)` → List[Dict]
- Lấy danh sách tất cả peers đã kết nối
- Chuyển từ PeerInfo object → dict
- **Return:** List các peer dict

#### `get_message_history(self, peer_id)` → List[Dict]
- Lấy lịch sử chat với peer_id
- Chuyển Message object → dict
- **Return:** List các message dict

#### `add_peer_by_ip(self, ip, port, display_name)` → (bool, Optional[str])
- Thêm peer mới bằng IP:Port
- Gửi friend request
- **Return:** (True, peer_id) hoặc (False, None)

#### `send_friend_request(self, peer_id)` → bool
- Gửi lời mời kết bạn đến peer_id

#### `accept_friend(self, peer_id)` → bool
- Chấp nhận lời mời kết bạn

#### `reject_friend(self, peer_id)` → bool
- Từ chối lời mời kết bạn

#### `start_call(self, peer_id, call_type)` → bool
- Bắt đầu cuộc gọi (voice hoặc video)
- Kiểm tra peer online
- Gọi `call_manager.start_outgoing_call()`
- Gửi CALL_REQUEST message qua TCP
- **Return:** True nếu gửi request thành công

#### `accept_call(self, peer_id)` → bool
- Chấp nhận cuộc gọi đến
- Gọi `call_manager.accept_incoming_call()`
- Gửi CALL_ACCEPT message
- Khởi động media streams (UDP)

#### `reject_call(self, peer_id)` → bool
- Từ chối cuộc gọi
- Gửi CALL_REJECT message

#### `end_call(self)` → bool
- Kết thúc cuộc gọi hiện tại
- Gửi CALL_END message
- Dừng media streams
- Emit signal `call_ended`

#### Các handler nội bộ
- `_handle_router_message()` - Xử lý tin nhắn từ router
- `_handle_peer_update()` - Xử lý cập nhật peer
- `_handle_friend_request()` - Xử lý lời mời kết bạn
- `_handle_call_request()` - Xử lý cuộc gọi đến
- `_handle_call_accept()` - Xử lý cuộc gọi được chấp nhận
- `_handle_call_reject()` - Xử lý cuộc gọi bị từ chối
- `_handle_call_end()` - Xử lý cuộc gọi kết thúc
- `_on_call_state_changed()` - Callback khi trạng thái call thay đổi
- `_on_remote_video_frame()` - Callback khi nhận frame video
- `_message_to_dict()` - Chuyển Message → dict
- `_peer_to_dict()` - Chuyển PeerInfo → dict

---

## 📞 `Core/call/call_manager.py` - QUẢN LÝ VIDEO/AUDIO CALL

### Enum: `CallState`
Trạng thái cuộc gọi:
- `IDLE` - Không có cuộc gọi
- `OUTGOING` - Đang gọi đi
- `INCOMING` - Có cuộc gọi đến
- `CONNECTED` - Đang trong cuộc gọi

### Enum: `CallType`
Loại cuộc gọi:
- `VOICE` - Chỉ âm thanh
- `VIDEO` - Video + âm thanh

### Class: `CallManager`

Quản lý luồng video/audio call.

#### `__init__(self)`
- Khởi tạo state = IDLE
- Tạo AudioCapture, AudioPlayback
- Tạo VideoCapture, VideoDecoder (nếu call video)
- Tạo UDPSender, UDPReceiver

#### `start_outgoing_call(self, peer_id, peer_name, peer_ip, call_type)` → (bool, int, int)
- Kiểm tra không đang trong cuộc gọi khác
- Cấp phát audio_port, video_port cho UDPReceiver
- Lưu thông tin peer
- Đặt state = OUTGOING
- **Return:** (True, audio_port, video_port) để gửi cho peer

#### `prepare_incoming_call(self, peer_id, peer_name, peer_ip, call_type, audio_port, video_port)` → bool
- Kiểm tra có thể nhận cuộc gọi không
- Lưu thông tin peer và ports
- Đặt state = INCOMING
- **Return:** True nếu có thể nhận

#### `accept_incoming_call(self)` → (bool, int, int)
- Kiểm tra state = INCOMING
- Cấp phát ports cho UDPReceiver của mình
- **Return:** (True, my_audio_port, my_video_port)

#### `start_media_streams(self, peer_audio_port, peer_video_port)` → bool
- Khởi động UDPReceiver (nhận audio/video từ peer)
- Khởi động AudioCapture (thu âm mic) + AudioPlayback (phát loa)
- Nếu VIDEO: Khởi động VideoCapture (thu camera)
- Khởi động UDPSender (gửi audio/video cho peer)
- Đặt state = CONNECTED
- **Return:** True nếu thành công

#### `end_call(self)`
- Dừng tất cả streams (Audio, Video, UDP)
- Đặt lại state = IDLE
- Reset thông tin peer

#### `is_in_call(self)` → bool
- Kiểm tra có đang trong cuộc gọi không
- **Return:** True nếu state != IDLE

#### `toggle_mute(self)`
- Bật/tắt microphone

#### `toggle_camera(self)`
- Bật/tắt camera (nếu video call)

**Callbacks:**
- `on_call_state_changed` - Được gọi khi state thay đổi
- `on_remote_video_frame` - Được gọi khi nhận frame video từ peer
- `on_error` - Được gọi khi có lỗi

---

## 🎤 `Core/media/audio_stream.py` - XỬ LÝ ÂM THANH

### Class: `AudioCapture`

Thu âm từ microphone và gửi qua UDP.

#### `__init__(self, udp_sender, peer_ip, peer_port)`
- Lưu UDPSender để gửi audio data
- Cấu hình: 16kHz, mono, 16-bit, chunk 1024 samples

#### `start(self)`
- Mở stream PyAudio từ microphone
- Tạo thread chạy `_capture_loop()`

#### `_capture_loop(self)`
- Vòng lặp vô tận:
  - Đọc chunk audio từ mic
  - Gửi qua UDP đến peer
  - Sleep 10ms

#### `stop(self)`
- Dừng thread
- Đóng stream PyAudio

#### `toggle_mute(self)`
- Bật/tắt mic

### Class: `AudioPlayback`

Nhận audio từ UDP và phát qua loa.

#### `__init__(self)`
- Tạo queue để buffer audio packets
- Cấu hình PyAudio output stream

#### `start(self)`
- Mở stream PyAudio output (loa)
- Tạo thread chạy `_playback_loop()`

#### `_playback_loop(self)`
- Vòng lặp vô tận:
  - Lấy audio data từ queue
  - Phát ra loa qua PyAudio

#### `put_audio_data(self, audio_bytes)`
- Nhận audio data từ UDPReceiver
- Đưa vào queue để phát

#### `stop(self)`
- Dừng thread
- Đóng stream

---

## 📹 `Core/media/video_stream.py` - XỬ LÝ VIDEO

### Class: `VideoCapture`

Thu video từ webcam và gửi qua UDP.

#### `__init__(self, udp_sender, peer_ip, peer_port)`
- Lưu UDPSender
- Cấu hình: 640x480, 15 FPS

#### `start(self)`
- Mở webcam bằng OpenCV (`cv2.VideoCapture`)
- Tạo thread chạy `_capture_loop()`

#### `_capture_loop(self)`
- Vòng lặp vô tận:
  - Đọc frame từ webcam
  - Resize về 640x480
  - Encode thành JPEG (chất lượng 70%)
  - Gửi qua UDP
  - Sleep để đạt 15 FPS

#### `stop(self)`
- Dừng thread
- Release webcam

#### `toggle_camera(self)`
- Bật/tắt camera

### Class: `VideoDecoder`

Nhận video từ UDP và decode để hiển thị.

#### `__init__(self, on_frame_callback)`
- Lưu callback để gửi frame đã decode
- Tạo queue buffer

#### `start(self)`
- Tạo thread chạy `_decode_loop()`

#### `_decode_loop(self)`
- Vòng lặp vô tận:
  - Lấy JPEG data từ queue
  - Decode bằng OpenCV
  - Gọi callback với frame đã decode

#### `put_video_data(self, video_bytes)`
- Nhận video data từ UDPReceiver
- Đưa vào queue để decode

#### `stop(self)`
- Dừng thread

---

## 🌐 `Core/networking/peer_client.py` - GỬI TIN NHẮN TCP

### Class: `PeerClient`

Client TCP để gửi tin nhắn đến peer.

#### `send(self, peer_ip, peer_port, message: Message)` → bool
- Chuyển Message thành JSON string
- Tạo TCP socket
- Connect đến peer_ip:peer_port
- Gửi JSON + "\n"
- **Return:** True nếu gửi thành công, False nếu peer offline

---

## 👂 `Core/networking/peer_listener.py` - LẮNG NGHE KẾT NỐI TCP

### Class: `PeerListener`

Server TCP lắng nghe kết nối từ peers khác.

#### `__init__(self, tcp_port, on_message_callback)`
- Lưu callback xử lý message
- Tạo server socket

#### `start(self)`
- Bind socket vào 0.0.0.0:tcp_port
- Listen tối đa 10 kết nối
- Tạo thread chạy `_accept_loop()`

#### `_accept_loop(self)`
- Vòng lặp vô tận:
  - Accept kết nối TCP mới
  - Tạo thread `_handle_client()` cho mỗi kết nối

#### `_handle_client(self, client_socket, client_address)`
- Đọc data từ socket
- Tách theo delimiter "\n"
- Parse JSON thành Message object
- Gọi callback với Message và client IP

#### `stop(self)`
- Dừng thread
- Đóng server socket

---

## 📡 `Core/networking/udp_stream.py` - GỬI/NHẬN UDP

### Class: `UDPSender`

Gửi audio/video data qua UDP.

#### `__init__(self)`
- Tạo UDP socket

#### `send_audio(self, audio_bytes, peer_ip, peer_port)`
- Gửi audio chunk qua UDP
- Format: "AUDIO:" + audio_bytes

#### `send_video(self, video_bytes, peer_ip, peer_port)`
- Gửi video frame qua UDP
- Format: "VIDEO:" + video_bytes

#### `close(self)`
- Đóng socket

### Class: `UDPReceiver`

Nhận audio/video data từ UDP.

#### `__init__(self, audio_port, video_port, on_audio_callback, on_video_callback)`
- Tạo 2 sockets: audio_socket và video_socket
- Bind vào audio_port và video_port

#### `start(self)`
- Tạo 2 threads:
  - `_receive_audio_loop()` - Nhận audio
  - `_receive_video_loop()` - Nhận video

#### `_receive_audio_loop(self)`
- Vòng lặp vô tận:
  - Nhận data từ audio_socket
  - Kiểm tra prefix "AUDIO:"
  - Gọi callback với audio_bytes

#### `_receive_video_loop(self)`
- Vòng lặp vô tận:
  - Nhận data từ video_socket
  - Kiểm tra prefix "VIDEO:"
  - Gọi callback với video_bytes

#### `stop(self)`
- Dừng threads
- Đóng sockets

---

## 💬 `Core/models/message.py` - CẤU TRÚC TIN NHẮN

### Class: `Message` (dataclass)

Đại diện cho một tin nhắn P2P.

**Thuộc tính:**
- `message_id: str` - ID duy nhất (UUID)
- `sender_id: str` - Peer ID người gửi
- `sender_name: str` - Tên hiển thị người gửi
- `receiver_id: str` - Peer ID người nhận
- `msg_type: str` - Loại tin nhắn (text, file, image, audio, status, friend_request, call_request, ...)
- `content: str` - Nội dung tin nhắn
- `timestamp: float` - Thời gian gửi (Unix timestamp)
- `file_name: Optional[str]` - Tên file (nếu là file/image)
- `file_data: Optional[str]` - Dữ liệu file base64
- `audio_data: Optional[str]` - Dữ liệu audio base64

#### Static methods tạo tin nhắn

##### `create_text(sender_id, sender_name, receiver_id, content)` → Message
Tạo tin nhắn văn bản thông thường.

##### `create_file(sender_id, sender_name, receiver_id, file_name, file_data)` → Message
Tạo tin nhắn gửi file (file_data là base64).

##### `create_image(...)` → Message
Tạo tin nhắn gửi ảnh.

##### `create_audio(...)` → Message
Tạo tin nhắn gửi audio.

##### `create_status_update(sender_id, sender_name, status)` → Message
Tạo tin nhắn thông báo trạng thái (online/offline/busy).

##### `create_friend_request(sender_id, sender_name, receiver_id)` → Message
Tạo lời mời kết bạn.

##### `create_friend_accept(...)` → Message
Chấp nhận lời mời kết bạn.

##### `create_friend_reject(...)` → Message
Từ chối lời mời kết bạn.

##### `create_call_request(sender_id, sender_name, receiver_id, call_type, audio_port, video_port)` → Message
Tạo yêu cầu cuộc gọi (gửi kèm ports để peer gửi media về).

##### `create_call_accept(...)` → Message
Chấp nhận cuộc gọi (gửi kèm ports của mình).

##### `create_call_reject(...)` → Message
Từ chối cuộc gọi.

##### `create_call_end(...)` → Message
Kết thúc cuộc gọi.

##### `create_unfriend(...)` → Message
Hủy kết bạn.

#### `to_json(self)` → str
Chuyển Message thành JSON string để gửi qua mạng.

#### `from_json(cls, json_str)` → Message
Parse JSON string thành Message object.

---

## 👥 `Core/models/peer_info.py` - THÔNG TIN PEER

### Class: `PeerInfo` (dataclass)

Lưu thông tin về một peer (người dùng khác).

**Thuộc tính:**
- `peer_id: str` - ID duy nhất của peer
- `display_name: str` - Tên hiển thị
- `ip: str` - Địa chỉ IP
- `tcp_port: int` - Port TCP để gửi tin nhắn
- `status: str` - Trạng thái (online, offline, busy)
- `last_seen: float` - Lần cuối thấy online (Unix timestamp)

#### `to_dict(self)` → Dict
Chuyển thành dictionary để lưu JSON.

#### `from_dict(cls, data)` → PeerInfo
Tạo PeerInfo từ dictionary.

---

## 🔀 `Core/routing/message_router.py` - BỘ ĐỊNH TUYẾN TIN NHẮN

### Class: `MessageRouter`

Lõi của hệ thống P2P, quản lý tất cả peers và tin nhắn.

#### `__init__(self)`
- Tạo peer_id duy nhất (UUID 8 ký tự)
- Khởi tạo dict `_peers` lưu tất cả peers
- Khởi tạo các sub-managers:
  - `PeerManager` - Quản lý danh sách peers
  - `FriendRequestManager` - Quản lý lời mời kết bạn
  - `MessageHandlers` - Xử lý tin nhắn đến
- Tạo lock để thread-safe

#### `connect_core(self, username, display_name, tcp_port, on_message_callback)`
- Lưu thông tin bản thân
- Khởi tạo DataManager (quản lý file/folder)
- Khởi tạo PeerMessageStorage (lưu tin nhắn)
- Khởi tạo PeerClient (gửi tin nhắn)
- Khởi tạo PeerListener (nhận tin nhắn)
- Khởi tạo StatusBroadcaster (phát trạng thái)
- Load danh sách peers từ `peers.json`
- Bắt đầu lắng nghe TCP
- Bắt đầu phát broadcast UDP

#### `send_message(self, peer_id, content, msg_type, ...)` → (bool, Optional[Message])
- Tìm peer trong `_peers`
- Tạo Message object
- Gửi qua PeerClient
- Lưu vào PeerMessageStorage
- **Return:** (success, message)

#### `add_peer_by_ip(self, ip, port, display_name)` → (bool, Optional[str])
- Tạo peer_id tạm thời
- Tạo PeerInfo mới
- Gửi STATUS_UPDATE để giới thiệu bản thân
- Gửi FRIEND_REQUEST
- Thêm vào `_peers`
- Lưu vào `peers.json`
- **Return:** (True, peer_id)

#### `send_friend_request(self, peer_id)` → bool
- Gọi FriendRequestManager để gửi request

#### `send_friend_accept(self, peer_id)` → bool
- Gọi FriendRequestManager để gửi accept

#### `send_friend_reject(self, peer_id)` → bool
- Gọi FriendRequestManager để gửi reject

#### `get_known_peers(self)` → List[PeerInfo]
- Trả về list tất cả peers

#### `get_message_history(self, peer_id)` → List[Message]
- Gọi PeerMessageStorage để lấy lịch sử chat

#### `stop(self)`
- Gửi STATUS_UPDATE (offline) đến tất cả peers
- Dừng PeerListener
- Dừng StatusBroadcaster

#### Callback setters
- `set_peer_callback()` - Set callback khi peer update
- `set_friend_request_callback()` - Set callback nhận friend request
- `set_friend_accepted_callback()` - Set callback friend accepted
- `set_friend_rejected_callback()` - Set callback friend rejected
- `set_call_request_callback()` - Set callback nhận call request
- `set_call_accept_callback()` - Set callback call accepted
- `set_call_reject_callback()` - Set callback call rejected
- `set_call_end_callback()` - Set callback call ended

---

## ⚙️ `Core/routing/message_handlers.py` - XỬ LÝ TIN NHẮN ĐẾN

### Class: `MessageHandlers`

Xử lý các loại tin nhắn đến từ peers.

#### `__init__(self, router)`
- Lưu reference đến MessageRouter

#### `handle_incoming_message(self, message: Message, sender_ip: str)`
- Kiểm tra `msg_type` của message
- Gọi handler tương ứng:
  - `text` → `_handle_text_message()`
  - `file`/`image`/`audio` → `_handle_file_message()`
  - `status_update` → `_handle_status_update()`
  - `friend_request` → `_handle_friend_request()`
  - `friend_accept` → `_handle_friend_accept()`
  - `friend_reject` → `_handle_friend_reject()`
  - `unfriend` → `_handle_unfriend()`
  - `call_request` → `_handle_call_request()`
  - `call_accept` → `_handle_call_accept()`
  - `call_reject` → `_handle_call_reject()`
  - `call_end` → `_handle_call_end()`

#### `_handle_text_message(self, message, sender_ip)`
- Lưu tin nhắn vào storage
- Gọi callback để GUI hiển thị

#### `_handle_file_message(self, message, sender_ip)`
- Decode base64 file_data
- Lưu file vào `data/.../chats/{peer_id}/files/`
- Lưu message vào storage
- Gọi callback

#### `_handle_status_update(self, message, sender_ip)`
- Kiểm tra sender_id có trong `_peers` chưa
- Nếu chưa có → tạo peer mới từ STATUS_UPDATE
- Cập nhật IP, port, status, last_seen
- Lưu vào peers.json
- Gọi peer_callback để GUI cập nhật

#### `_handle_friend_request(self, message, sender_ip)`
- Cập nhật/tạo peer
- Gọi friend_request_callback → GUI hiện dialog

#### `_handle_friend_accept(self, message, sender_ip)`
- Đánh dấu peer là bạn bè chính thức
- Gọi friend_accepted_callback

#### `_handle_friend_reject(self, message, sender_ip)`
- Gọi friend_rejected_callback

#### `_handle_unfriend(self, message, sender_ip)`
- Xóa peer khỏi `_peers`
- Xóa khỏi peers.json
- (Có thể giữ lại tin nhắn cũ)

#### `_handle_call_request(self, message, sender_ip)`
- Lấy call_type, audio_port, video_port từ message.content
- Gọi call_request_callback → GUI hiện CallDialog

#### `_handle_call_accept(self, message, sender_ip)`
- Lấy ports từ message.content
- Gọi call_accept_callback → GUI bắt đầu streams

#### `_handle_call_reject(self, message, sender_ip)`
- Gọi call_reject_callback

#### `_handle_call_end(self, message, sender_ip)`
- Gọi call_end_callback → GUI đóng call window

---

## 🤝 `Core/routing/friend_request_manager.py` - QUẢN LÝ LỜI MỜI KẾT BẠN

### Class: `FriendRequestManager`

Xử lý logic gửi/nhận lời mời kết bạn.

#### `__init__(self, router)`
- Lưu reference đến router

#### `send_friend_request(self, peer_id)` → bool
- Tìm peer trong router._peers
- Tạo Message FRIEND_REQUEST
- Gửi qua PeerClient
- **Return:** True nếu gửi thành công

#### `send_friend_accept(self, peer_id)` → bool
- Tạo Message FRIEND_ACCEPT
- Gửi đến peer
- Đánh dấu peer là "accepted"

#### `send_friend_reject(self, peer_id)` → bool
- Tạo Message FRIEND_REJECT
- Gửi đến peer

---

## 👨‍👩‍👧‍👦 `Core/routing/peer_manager.py` - QUẢN LÝ DANH SÁCH PEERS

### Class: `PeerManager`

Quản lý danh sách peers và trạng thái của họ.

#### `__init__(self, router)`
- Lưu reference đến router

#### `get_known_peers(self)` → List[PeerInfo]
- Trả về list tất cả peers từ router._peers

#### `cleanup_offline_peers(self, max_offline_time=600)` → int
- Kiểm tra last_seen của các peers
- Nếu offline quá lâu (>10 phút) → có thể xóa
- **Return:** Số peers bị xóa
- (Hiện tại trả về 0 - chưa implement)

#### `notify_existing_peers(self)`
- Duyệt tất cả peers
- Gọi peer_callback cho từng peer
- Để GUI refresh danh sách khi khởi động

---

## 📢 `Core/routing/status_broadcaster.py` - PHÁT TRẠNG THÁI

### Class: `StatusBroadcaster`

Phát trạng thái online/offline đến tất cả peers định kỳ.

#### `__init__(self, router)`
- Lưu reference đến router
- Cấu hình interval: 30 giây/lần

#### `start(self)`
- Tạo thread chạy `_broadcast_loop()`

#### `_broadcast_loop(self)`
- Vòng lặp vô tận:
  - Sleep 30 giây
  - Gọi `send_status_to_all_peers("online")`

#### `send_status_to_all_peers(self, status)`
- Duyệt tất cả peers trong router._peers
- Gửi STATUS_UPDATE message đến từng peer

#### `send_status_to_peer(self, peer_id, status)`
- Gửi STATUS_UPDATE đến một peer cụ thể
- Dùng khi muốn thông báo offline trước khi thoát app

#### `stop(self)`
- Gửi offline status đến tất cả
- Dừng thread

---

## 💾 `Core/storage/data_manager.py` - QUẢN LÝ FILE/FOLDER

### Class: `DataManager`

Quản lý cấu trúc thư mục và file của user.

#### `__init__(self, username)`
- Tạo đường dẫn: `data/{username}/`
- Tạo thư mục nếu chưa có

#### `get_user_dir(self)` → Path
- Trả về đường dẫn thư mục user

#### `get_profile_path(self)` → Path
- Trả về đường dẫn `profile.json`

#### `get_peers_file(self)` → Path
- Trả về đường dẫn `peers.json`

#### `get_peer_chat_dir(self, peer_id)` → Path
- Trả về đường dẫn `chats/{peer_id}/`
- Tạo thư mục nếu chưa có

#### `get_peer_messages_file(self, peer_id)` → Path
- Trả về đường dẫn `chats/{peer_id}/messages.json`

#### `get_peer_files_dir(self, peer_id)` → Path
- Trả về đường dẫn `chats/{peer_id}/files/`
- Tạo thư mục nếu chưa có

#### `save_file_for_peer(self, peer_id, file_name, file_bytes)` → Path
- Lưu file vào `chats/{peer_id}/files/{file_name}`
- **Return:** Đường dẫn file đã lưu

#### `load_peers(self)` → Dict[str, PeerInfo]
- Đọc `peers.json`
- Parse thành dict {peer_id: PeerInfo}
- **Return:** Dict peers

#### `save_peers(self, peers: Dict[str, PeerInfo])`
- Chuyển peers thành dict
- Lưu vào `peers.json`

---

## 💬 `Core/storage/peer_message_storage.py` - LƯU TIN NHẮN

### Class: `PeerMessageStorage`

Lưu trữ lịch sử tin nhắn với từng peer riêng biệt.

#### `__init__(self, data_manager)`
- Lưu reference DataManager

#### `save_message(self, peer_id, message: Message)`
- Đọc messages.json hiện tại
- Append message mới
- Ghi lại file

#### `load_messages(self, peer_id)` → List[Message]
- Đọc `chats/{peer_id}/messages.json`
- Parse thành list Message objects
- **Return:** List messages

#### `get_last_message(self, peer_id)` → Optional[Message]
- Load tất cả messages
- **Return:** Message cuối cùng hoặc None

---

## ⚙️ `Core/utils/config.py` - CẤU HÌNH HỆ THỐNG

File chứa các hằng số cấu hình:

```python
TCP_BASE_PORT = 55000           # Port cơ sở cho TCP
TCP_CONNECT_TIMEOUT = 5.0       # Timeout kết nối TCP (giây)
UDP_BROADCAST_PORT = 55100      # Port phát broadcast UDP
STATUS_BROADCAST_INTERVAL = 30  # Interval phát status (giây)
```

---

## 🌐 `Core/utils/network_mode.py` - XÁC ĐỊNH IP MẠNG

### Hàm tiện ích

#### `get_local_ip(network_mode=None)` → str
- Tự động xác định IP của máy trong mạng LAN
- Bỏ qua adapter ảo (VirtualBox, VMware, Docker)
- Ưu tiên dải IP LAN (192.168.x.x, 10.x.x.x)
- **Return:** Địa chỉ IP string

#### `get_broadcast_address(network_mode=None)` → str
- Tính địa chỉ broadcast từ IP và subnet mask
- VD: 192.168.1.5/24 → 192.168.1.255
- **Return:** Địa chỉ broadcast

#### `detect_network_mode()` → str
- Phát hiện loại mạng (LAN, WiFi, Loopback)
- **Return:** "LAN" hoặc "LOOPBACK"

#### `_get_all_network_ips()` → List[Tuple[str, str]]
- Lấy tất cả IP của các interface mạng
- **Return:** [(ip, interface_name), ...]

#### `_is_lan_ip(ip: str)` → bool
- Kiểm tra IP có phải dải LAN không
- **Return:** True nếu 192.168.x.x hoặc 10.x.x.x

#### `_is_virtual_adapter(ip: str)` → bool
- Kiểm tra IP có phải từ adapter ảo không
- **Return:** True nếu là VirtualBox, VMware, Docker

---

## 🖥️ `Gui/view/main_window.py` - MÀN HÌNH CHÍNH

### Class: `MainWindow` (QMainWindow)

Cửa sổ chính của ứng dụng sau khi đăng nhập.

#### `__init__(self, user_name, user_id, username, avatar_path, tcp_port)`
- Lưu thông tin user
- Tạo MainWindowController
- Setup UI với layout 3 cột:
  - Cột trái: Thông tin user + ChatList
  - Cột giữa: ChatArea
  - Cột phải: NotificationsPanel
- Kết nối signals từ controller

#### `_setup_ui(self)`
- Tạo central_widget với QHBoxLayout
- Tạo left panel:
  - Avatar + display name
  - Nút Add Friend
  - ChatListWidget
- Tạo center panel:
  - ChatAreaWidget
- Tạo right panel:
  - NotificationsPanelWidget
- Set window size: 1400x800

#### `_setup_connections(self)`
- Kết nối signals từ controller:
  - chat_list_updated → _update_chat_list
  - load_chat_history → _load_chat_history
  - show_friend_request_dialog → _show_friend_request_dialog
  - show_message_box → _show_message_box
- Kết nối sự kiện UI:
  - ChatList item click → controller.select_chat()
  - ChatArea send_message → controller.send_text_message()
  - Add Friend button → _show_add_friend_dialog()

#### `_show_add_friend_dialog(self)`
- Hiện dialog nhập IP:Port
- Gọi controller.add_friend_by_ip()

#### `_show_friend_request_dialog(self, peer_id, display_name)`
- Hiện dialog "X muốn kết bạn với bạn"
- Nút Accept → controller.accept_friend()
- Nút Reject → controller.reject_friend()

#### `_update_chat_list(self, chat_items)`
- Cập nhật danh sách chat với data mới

#### `_load_chat_history(self, peer_id, messages)`
- Load lịch sử chat vào ChatArea
- Clear messages cũ
- Add từng message bubble

#### `closeEvent(self, event)`
- Override để cleanup khi đóng app
- Gọi controller.cleanup() để dừng Core
- Gửi offline status

---

## 💬 `Gui/view/chat_area.py` - KHU VỰC CHAT

### Class: `ChatAreaWidget` (QWidget)

Widget hiển thị tin nhắn và input gửi tin nhắn.

#### `__init__(self)`
- Tạo layout dọc:
  - Header (tên peer, nút call)
  - Scroll area (hiển thị messages)
  - Input area (gõ tin nhắn + nút gửi)
- Khởi tạo current_peer_id = None

#### `set_peer(self, peer_id, display_name, status)`
- Set peer đang chat
- Update header với tên và trạng thái

#### `clear_messages(self)`
- Xóa tất cả message bubbles

#### `add_message(self, message_data: dict)`
- Tạo MessageBubble từ message_data
- Thêm vào scroll area
- Tự động scroll xuống cuối

#### `_send_message(self)`
- Lấy text từ input
- Emit signal send_message với text
- Clear input

#### `_show_emoji_picker(self)`
- Hiện dialog chọn emoji
- Click emoji → insert vào input

#### `_attach_file(self)`
- Mở file dialog chọn file
- Đọc file thành bytes
- Encode base64
- Emit signal send_file với file_name và file_data

#### `_attach_image(self)`
- Tương tự _attach_file nhưng filter chỉ ảnh

#### `_start_voice_call(self)`
- Emit signal start_call với call_type="voice"

#### `_start_video_call(self)`
- Emit signal start_call với call_type="video"

**Signals:**
- `send_message = Signal(str)` - Gửi tin nhắn text
- `send_file = Signal(str, bytes)` - Gửi file
- `start_call = Signal(str)` - Bắt đầu cuộc gọi

---

## 📝 `Gui/view/message_bubble.py` - BONG BÓNG TIN NHẮN

### Class: `MessageBubble` (QFrame)

Widget hiển thị một tin nhắn.

#### `__init__(self, message_data, is_sender)`
- `is_sender`: True nếu mình gửi, False nếu nhận
- Layout tùy theo msg_type:
  - `text`: Hiện nội dung text
  - `file`: Hiện icon file + tên file + nút download
  - `image`: Hiện thumbnail ảnh
  - `audio`: Hiện player audio

#### `_create_text_message(self)`
- Tạo QLabel với content
- Set style theo sender/receiver

#### `_create_file_message(self)`
- Tạo icon file
- Tạo label tên file
- Tạo nút Download (nếu chưa có file local)

#### `_create_image_message(self)`
- Load ảnh từ file_data (base64)
- Hiện thumbnail 200x200
- Click ảnh → mở full size

#### `_download_file(self)`
- Decode base64 file_data
- Lưu file vào đường dẫn user chọn

---

## 📋 `Gui/view/chat_list.py` - DANH SÁCH HỘI THOẠI

### Class: `ChatListWidget` (QWidget)

Widget hiển thị danh sách các hội thoại.

#### `__init__(self)`
- Tạo QVBoxLayout với list các ChatItemWidget
- Tạo scroll area

#### `update_chat_list(self, chat_items)`
- Clear danh sách cũ
- Tạo ChatItemWidget cho mỗi chat_item
- Thêm vào layout
- Kết nối click event

#### `set_active_chat(self, peer_id)`
- Đánh dấu chat đang active
- Highlight item tương ứng

**Signals:**
- `chat_selected = Signal(str, str)` - (peer_id, display_name)

---

## 📌 `Gui/view/chat_item.py` - ITEM TRONG DANH SÁCH

### Class: `ChatItemWidget` (QFrame)

Widget đại diện cho một hội thoại trong list.

#### `__init__(self, name, message, time, unread_count, is_active)`
- `name`: Tên peer
- `message`: Tin nhắn cuối cùng
- `time`: Thời gian tin nhắn cuối
- `unread_count`: Số tin chưa đọc
- `is_active`: Có đang chat không

#### Layout:
- Avatar (nếu có)
- Tên + tin nhắn cuối
- Thời gian + badge unread count

#### `mousePressEvent(self, event)`
- Override để bắt sự kiện click
- Emit signal hoặc callback

---

## 🔔 `Gui/view/notifications_panel.py` - PANEL THÔNG BÁO

### Class: `NotificationsPanelWidget` (QWidget)

Panel bên phải hiển thị thông báo và thông tin mạng.

#### `__init__(self)`
- Tạo layout dọc:
  - Tiêu đề "Notifications"
  - Scroll area notifications
  - Network info (LAN IP, Peer ID, Port)

#### `add_notification(self, text, notification_type)`
- Thêm notification mới vào list
- notification_type: "info", "success", "warning", "error"
- Tự động scroll xuống cuối

#### `set_network_info(self, peer_id, local_ip, tcp_port)`
- Cập nhật thông tin mạng hiển thị

---

## 📞 `Gui/view/call_dialog.py` - DIALOG CUỘC GỌI ĐẾN

### Class: `CallDialog` (QDialog)

Dialog hiện khi có cuộc gọi đến.

#### `__init__(self, caller_name, call_type, parent)`
- `caller_name`: Tên người gọi
- `call_type`: "voice" hoặc "video"
- Hiện avatar + tên + "đang gọi bạn"
- Nút Accept (xanh)
- Nút Reject (đỏ)

**Signals:**
- `call_accepted = Signal()` - Chấp nhận cuộc gọi
- `call_rejected = Signal()` - Từ chối cuộc gọi

---

## 🎥 `Gui/view/call_window.py` - CỬA SỔ VIDEO CALL

### Class: `CallWindow` (QWidget)

Cửa sổ hiển thị video call.

#### `__init__(self, peer_name, call_type, chat_core)`
- `peer_name`: Tên người đang gọi
- `call_type`: "voice" hoặc "video"
- `chat_core`: Reference để nhận video frames

#### Layout:
- Video area:
  - Remote video (video của peer) - kích thước lớn
  - Local video (video của mình) - kích thước nhỏ, góc phải trên
- Controls panel (dưới cùng):
  - Nút Mute/Unmute
  - Nút End Call (đỏ)
  - Nút Camera On/Off

#### `update_remote_video(self, frame_bytes)`
- Nhận frame từ signal remote_video_frame
- Decode frame
- Hiển thị trong remote_video_label

#### `update_local_video(self, frame)`
- Cập nhật preview camera local

#### `_toggle_mute(self)`
- Gọi chat_core.call_manager.toggle_mute()
- Đổi icon nút

#### `_toggle_camera(self)`
- Gọi chat_core.call_manager.toggle_camera()
- Đổi icon nút

#### `_end_call(self)`
- Gọi chat_core.end_call()
- Đóng cửa sổ

---

## 🎨 `Gui/view/stylesheet.py` - CSS CHÍNH

File chứa **STYLESHEET** - chuỗi CSS định nghĩa toàn bộ giao diện ứng dụng.

Định nghĩa style cho:
- MainWindow, panels
- ChatListWidget, ChatItemWidget
- ChatAreaWidget, MessageBubble
- Input fields, buttons
- Scroll bars
- Call controls
- Network info labels
- ...

Tất cả style được tập trung ở đây, không có style inline trong code.

---

## 🔐 `Gui/view/auth_stylesheet.py` - CSS ĐĂNG NHẬP

File chứa **AUTH_STYLESHEET** - CSS cho màn hình đăng nhập/đăng ký.

Định nghĩa style cho:
- LoginCard (card trắng nổi trên nền xanh)
- CardTitle (tiêu đề "Login"/"Register")
- UnderlineInput (input với underline)
- ModernPrimaryButton (nút xanh gradient)
- TextLink, ColoredLink
- AvatarPreview, UploadAvatarButton
- EyeIcon (icon show/hide password)

---

## 🎮 `Gui/controller/main_window_controller.py` - CONTROLLER CHÍNH

### Class: `MainWindowController` (QObject)

Controller điều khiển logic cho MainWindow.

#### `__init__(self, username, display_name, tcp_port)`
- Tạo ChatCore với thông tin user
- Khởi tạo dict theo dõi peers và unread_counts
- Tạo QTimer để refresh status định kỳ

#### `start(self)`
- Gọi chat_core.start() để bắt đầu P2P
- Kết nối các signals từ chat_core
- Thông báo network info lên GUI
- Refresh chat list ban đầu
- Bắt đầu timer

#### `cleanup(self)`
- Dừng timer
- Gọi chat_core.stop()
- Gửi offline status

#### `select_chat(self, peer_id)`
- Set current_peer_id
- Load message history
- Emit signal load_chat_history
- Reset unread count

#### `send_text_message(self, content)`
- Gọi chat_core.send_message() với current_peer_id
- Cập nhật chat list

#### `send_file_message(self, file_name, file_bytes)`
- Encode file thành base64
- Gọi chat_core.send_message() với msg_type="file"

#### `send_image_message(self, file_name, image_bytes)`
- Encode ảnh thành base64
- Gọi chat_core.send_message() với msg_type="image"

#### `add_friend_by_ip(self, ip, port)`
- Gọi chat_core.add_peer_by_ip()
- Nếu thành công → refresh chat list

#### `accept_friend(self, peer_id)`
- Gọi chat_core.accept_friend()
- Refresh chat list

#### `reject_friend(self, peer_id)`
- Gọi chat_core.reject_friend()

#### `remove_friend(self, peer_id)`
- Gửi STATUS_UPDATE offline
- Xóa peer khỏi danh sách
- Refresh chat list

#### `start_call(self, call_type)`
- Gọi chat_core.start_call() với current_peer_id
- Mở CallWindow

#### Các callback nhận sự kiện từ Core

##### `_on_message_received_signal(self, message_dict)`
- Nhận tin nhắn mới
- Emit signal message_received
- Cập nhật unread count
- Refresh chat list

##### `_on_peer_updated_signal(self, peer_dict)`
- Peer thay đổi trạng thái
- Cập nhật dict peers
- Refresh chat list

##### `_on_friend_request_received_signal(self, peer_id, display_name)`
- Nhận lời mời kết bạn
- Emit signal show_friend_request_dialog

##### `_on_call_request_received(self, peer_id, peer_name, call_type)`
- Nhận cuộc gọi đến
- Hiện CallDialog
- Accept → chat_core.accept_call()
- Reject → chat_core.reject_call()

##### `_on_call_accepted(self, peer_id)`
- Cuộc gọi được chấp nhận
- Mở CallWindow

##### `_on_call_rejected(self, peer_id)`
- Cuộc gọi bị từ chối
- Hiện thông báo

##### `_on_call_ended(self, peer_id)`
- Cuộc gọi kết thúc
- Đóng CallWindow

#### `_refresh_chat_list(self)`
- Lấy danh sách peers từ chat_core
- Lấy tin nhắn cuối của mỗi peer
- Sắp xếp theo thời gian
- Emit signal chat_list_updated

**Signals:**
- `chat_list_updated = Signal(list)` - Danh sách chat đã thay đổi
- `message_received = Signal(dict)` - Nhận tin nhắn mới
- `chat_selected = Signal(str, str)` - Chọn chat
- `show_friend_request_dialog = Signal(str, str)` - Hiện dialog friend request
- `show_message_box = Signal(str, str, str)` - Hiện message box
- `load_chat_history = Signal(str, list)` - Load lịch sử chat

---

## 🎮 `Gui/controller/chat_area_controller.py` - CONTROLLER CHAT AREA

### Class: `ChatAreaController` (QObject)

Controller điều khiển ChatAreaWidget (hiện không dùng nhiều, logic ở MainWindowController).

#### `__init__(self, chat_area_widget)`
- Lưu reference widget
- Setup connections

---

## 🎮 `Gui/controller/chat_list_controller.py` - CONTROLLER CHAT LIST

### Class: `ChatListController` (QObject)

Controller điều khiển ChatListWidget (hiện không dùng nhiều, logic ở MainWindowController).

#### `__init__(self, chat_list_widget)`
- Lưu reference widget
- Setup connections

---

## 🛠️ `Gui/utils/avatar.py` - XỬ LÝ AVATAR

### Hàm tiện ích

#### `load_circular_pixmap(image_path, size, border_width)` → QPixmap
- Load ảnh từ đường dẫn
- Crop thành hình tròn
- Vẽ viền (tùy chọn)
- **Return:** QPixmap hình tròn

---

## 🛠️ `Gui/utils/elide_label.py` - LABEL RÚT GỌN

### Class: `ElideLabel` (QLabel)

QLabel tự động rút gọn text nếu quá dài.

#### `paintEvent(self, event)`
- Override để vẽ text với elide (...)
- VD: "Đây là tin nhắn rất dài..." → "Đây là tin nhắn..."

---

## 🔧 `migrate_messages_to_per_peer.py` - SCRIPT CHUYỂN ĐỔI DỮ LIỆU

Script một lần để migrate dữ liệu từ format cũ sang mới.

### Hàm chính

#### `migrate_user_data(username)`
- Đọc `messages.json` (format cũ - tất cả tin nhắn trong 1 file)
- Nhóm tin nhắn theo peer_id
- Tạo folder `chats/{peer_id}/` cho mỗi peer
- Lưu tin nhắn vào `chats/{peer_id}/messages.json`
- Backup file cũ

#### `migrate_all_users()`
- Duyệt tất cả user trong `data/`
- Gọi migrate_user_data() cho mỗi user

**Chạy script:**
```bash
python migrate_messages_to_per_peer.py
```

---

## 🎯 LUỒNG HOẠT ĐỘNG CHI TIẾT

### 🔐 Luồng Đăng nhập

1. User chạy `main.py`
2. `ChatApplication` khởi động
3. Hiển thị `LoginWindow`
4. User nhập email + password
5. `LoginWindow._login()` gọi `user_manager.login()`
6. `UserManager` tìm user trong `data/`
7. So sánh password_hash
8. Nếu đúng: Emit signal `login_successful` với User object
9. `ChatApplication.on_login_success()` nhận signal
10. Gọi `show_main_window()`
11. Tạo `MainWindow` với thông tin user
12. `MainWindow.__init__()` tạo `MainWindowController`
13. `MainWindowController.__init__()` tạo `ChatCore`
14. Hiển thị `MainWindow`
15. Gọi `controller.start()`

### 🚀 Luồng Khởi động Core

1. `MainWindowController.start()` gọi `chat_core.start()`
2. `ChatCore.start()` gọi `router.connect_core()`
3. `MessageRouter.connect_core()`:
   - Khởi tạo `DataManager`
   - Khởi tạo `PeerMessageStorage`
   - Khởi tạo `PeerClient`
   - Khởi tạo `PeerListener` → bắt đầu lắng nghe TCP
   - Khởi tạo `StatusBroadcaster` → bắt đầu phát UDP
   - Load peers từ `peers.json`
4. `StatusBroadcaster` gửi STATUS_UPDATE (online) đến tất cả peers
5. Các peers nhận được sẽ cập nhật trạng thái
6. `MessageHandlers._handle_status_update()` cập nhật peer
7. Emit signal `peer_updated`
8. GUI nhận signal → hiển thị peer online

### 💬 Luồng Gửi tin nhắn

1. User gõ tin nhắn trong `ChatAreaWidget`
2. Click nút Send
3. `ChatAreaWidget` emit signal `send_message`
4. `MainWindowController.send_text_message()` nhận signal
5. Gọi `chat_core.send_message(peer_id, content)`
6. `ChatCore.send_message()` gọi `router.send_message()`
7. `MessageRouter.send_message()`:
   - Tạo `Message` object
   - Gọi `peer_client.send()` để gửi TCP
   - Gọi `peer_message_storage.save_message()` để lưu
8. `PeerClient.send()`:
   - Convert Message → JSON
   - Tạo TCP socket
   - Connect đến peer IP:Port
   - Send JSON
9. Tin nhắn đã gửi → GUI hiển thị bubble

### 📨 Luồng Nhận tin nhắn

1. Peer A gửi tin nhắn → TCP packet đến
2. `PeerListener._accept_loop()` accept connection
3. `PeerListener._handle_client()`:
   - Đọc JSON từ socket
   - Parse thành `Message` object
   - Gọi callback với Message
4. `MessageRouter` nhận callback
5. `MessageHandlers.handle_incoming_message()`:
   - Kiểm tra `msg_type`
   - Gọi handler tương ứng
6. `MessageHandlers._handle_text_message()`:
   - Lưu message vào storage
   - Gọi callback → `ChatCore._handle_router_message()`
7. `ChatCore._emit_message()`:
   - Convert Message → dict
   - Emit signal `message_received`
8. `MainWindowController._on_message_received_signal()` nhận signal
9. Emit signal đến GUI
10. GUI thêm `MessageBubble` mới

### 📞 Luồng Video Call

#### Bắt đầu cuộc gọi (Caller)

1. User A click nút video call
2. `ChatAreaWidget` emit signal `start_call("video")`
3. `MainWindowController.start_call()` nhận signal
4. Gọi `chat_core.start_call(peer_id, "video")`
5. `ChatCore.start_call()`:
   - Gọi `call_manager.start_outgoing_call()`
   - `CallManager` cấp phát audio_port, video_port
   - Tạo Message CALL_REQUEST với ports
   - Gửi qua TCP đến peer B
6. `CallManager` set state = OUTGOING
7. GUI mở `CallWindow` với trạng thái "Đang gọi..."

#### Nhận cuộc gọi (Callee)

1. Peer B nhận CALL_REQUEST qua TCP
2. `MessageHandlers._handle_call_request()`:
   - Lấy call_type, audio_port, video_port
   - Gọi `chat_core._handle_call_request()`
3. `ChatCore._handle_call_request()`:
   - Gọi `call_manager.prepare_incoming_call()`
   - Emit signal `call_request_received`
4. `MainWindowController._on_call_request_received()` nhận signal
5. Hiển thị `CallDialog` "A đang gọi bạn"
6. User B click Accept:
   - Gọi `chat_core.accept_call(peer_id)`
   - `ChatCore.accept_call()`:
     - Gọi `call_manager.accept_incoming_call()`
     - Cấp phát ports của B
     - Tạo Message CALL_ACCEPT với ports
     - Gửi về peer A
     - Gọi `call_manager.start_media_streams()`

#### Bắt đầu streams

1. Peer A nhận CALL_ACCEPT
2. `MessageHandlers._handle_call_accept()`:
   - Lấy ports của B
   - Gọi `chat_core._handle_call_accept()`
3. `ChatCore._handle_call_accept()`:
   - Gọi `call_manager.start_media_streams(peer_ports)`
4. `CallManager.start_media_streams()`:
   - Khởi động `UDPReceiver` (nhận audio/video từ peer)
   - Khởi động `AudioCapture` (thu mic)
   - Khởi động `VideoCapture` (thu camera)
   - Khởi động `AudioPlayback` (phát loa)
   - Khởi động `UDPSender` (gửi audio/video)
5. `AudioCapture._capture_loop()`:
   - Đọc audio từ mic
   - Gửi qua UDP đến peer port
6. `UDPReceiver._receive_audio_loop()`:
   - Nhận audio từ UDP
   - Gọi callback → `AudioPlayback.put_audio_data()`
7. `AudioPlayback._playback_loop()`:
   - Lấy audio từ queue
   - Phát ra loa
8. `VideoCapture._capture_loop()`:
   - Đọc frame từ webcam
   - Encode JPEG
   - Gửi qua UDP
9. `UDPReceiver._receive_video_loop()`:
   - Nhận video từ UDP
   - Gọi callback → `VideoDecoder.put_video_data()`
10. `VideoDecoder._decode_loop()`:
    - Decode JPEG
    - Gọi callback → `CallManager._on_remote_video_frame()`
11. `CallManager` emit signal `remote_video_frame`
12. `ChatCore` forward signal
13. `CallWindow.update_remote_video()` nhận signal
14. Hiển thị video của peer

#### Kết thúc cuộc gọi

1. User click End Call
2. `CallWindow._end_call()` gọi `chat_core.end_call()`
3. `ChatCore.end_call()`:
   - Tạo Message CALL_END
   - Gửi qua TCP
   - Gọi `call_manager.end_call()`
4. `CallManager.end_call()`:
   - Dừng tất cả captures, playbacks, streams
   - Set state = IDLE
5. Peer nhận CALL_END:
   - Gọi `call_manager.end_call()`
   - Đóng `CallWindow`

---

## 📊 SƠ ĐỒ PHÂN LỚP

```
┌─────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                    │
│              (Gui/view + Gui/controller)                 │
│  - MainWindow, ChatArea, ChatList, CallWindow            │
│  - MainWindowController xử lý UI logic                   │
└──────────────────────┬──────────────────────────────────┘
                       │ Signals / Slots
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    API LAYER                             │
│                 (Core/core_api.py)                       │
│  - ChatCore: API giao tiếp giữa GUI và Core              │
│  - CoreSignals: Phát sự kiện lên GUI                     │
└──────────────────────┬──────────────────────────────────┘
                       │ Method Calls
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                  │
│         (Core/routing + Core/call + Core/media)          │
│  - MessageRouter: Định tuyến tin nhắn P2P                │
│  - CallManager: Quản lý cuộc gọi                         │
│  - AudioStream, VideoStream: Xử lý media                 │
└──────────────────────┬──────────────────────────────────┘
                       │ Uses
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    NETWORKING LAYER                      │
│                (Core/networking)                         │
│  - PeerListener: Lắng nghe TCP                           │
│  - PeerClient: Gửi TCP                                   │
│  - UDPSender, UDPReceiver: UDP streaming                 │
└──────────────────────┬──────────────────────────────────┘
                       │ Stores/Loads
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    DATA LAYER                            │
│              (Core/storage + Core/models)                │
│  - DataManager: Quản lý file/folder                      │
│  - PeerMessageStorage: Lưu tin nhắn                      │
│  - Message, PeerInfo: Data models                        │
└─────────────────────────────────────────────────────────┘
```

---

## 🎓 KIẾN THỨC CẦN THIẾT

### 1. **Python Basics**
- Classes, inheritance
- Threading
- Exception handling
- File I/O, JSON

### 2. **PySide6 (Qt)**
- QWidget, QMainWindow
- Signals & Slots
- Layouts (QVBoxLayout, QHBoxLayout)
- Stylesheets (CSS-like)

### 3. **Networking**
- TCP sockets
- UDP sockets
- Client-Server model
- P2P architecture

### 4. **Audio/Video**
- PyAudio (microphone, speaker)
- OpenCV (webcam, video processing)
- JPEG encoding/decoding

### 5. **Data Structures**
- Queues (threading.Queue)
- Dictionaries, Lists
- JSON serialization

---

## 🐛 DEBUGGING VÀ LOGS

- Mỗi module có `log = logging.getLogger(__name__)`
- Log level: DEBUG, INFO, WARNING, ERROR
- Logs hiện ở console khi chạy app
- Quan sát logs để debug vấn đề kết nối, tin nhắn

---

## 📌 LƯU Ý QUAN TRỌNG

1. **Port conflicts**: Nếu port bị chiếm, app sẽ tự cấp phát port khác
2. **Firewall**: Cần mở port TCP/UDP trong firewall để P2P hoạt động
3. **Same network**: Các peers phải cùng mạng LAN
4. **File size**: Gửi file lớn có thể chậm (không có chunking)
5. **Video quality**: Giảm quality để giảm bandwidth
6. **Thread safety**: Sử dụng locks khi truy cập shared data

---

## 🚀 CÁC TÍNH NĂNG CÓ THỂ MỞ RỘNG

- [ ] Encryption (mã hóa tin nhắn)
- [ ] Group chat (chat nhóm)
- [ ] File transfer với progress bar
- [ ] Screen sharing
- [ ] Emoji reactions
- [ ] Voice messages
- [ ] Search messages
- [ ] Export chat history
- [ ] Custom themes
- [ ] Notification sounds
- [ ] Status: online/offline/busy/away

---

## ✅ HOÀN THÀNH!

Đây là toàn bộ giải thích chi tiết về dự án Chat P2P. Hy vọng tài liệu này giúp bạn hiểu rõ cách thức hoạt động của từng thành phần! 🎉

Nếu có bất kỳ thắc mắc nào về file cụ thể hoặc hàm nào đó, hãy hỏi thêm nhé!

