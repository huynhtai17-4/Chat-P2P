# 📊 PHÂN TÍCH CẤU TRÚC THƯ MỤC /CORE THEO THỨ TỰ LOGIC

> **Mục đích:** Giải thích từng bước một cách logic nhất về cấu trúc thư mục Core, từ file cơ bản nhất đến file phức tạp nhất, giúp người mới hiểu được toàn bộ luồng xây dựng hệ thống P2P.

---

## 🎯 TỔNG QUAN CHIẾN LƯỢC XÂY DỰNG

Thư mục `/Core` được xây dựng theo nguyên tắc **từ dưới lên (Bottom-Up)**:
1. **Nền tảng** → Constants, Utils, Data Models
2. **Tầng dữ liệu** → Storage, File Management  
3. **Tầng giao tiếp** → Networking (TCP/UDP)
4. **Tầng xử lý media** → Audio/Video Streaming
5. **Tầng logic nghiệp vụ** → Routing, Message Handling
6. **Tầng tích hợp** → Call Manager
7. **Tầng API** → Core API (giao diện với GUI)

---

## 📚 PHÂN TÍCH CHI TIẾT TỪNG BƯỚC

---

### **BƯỚC 1: File Constants và Configuration**

#### 📄 File: `Core/utils/config.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/utils/config.py`
- **Loại:** File constants (hằng số cấu hình)
- **Dung lượng:** ~10 dòng code

**2. Chức năng chính trong bộ Core:**
```python
TCP_BASE_PORT = 55000           # Port mặc định cho TCP server
TCP_CONNECT_TIMEOUT = 5.0       # Timeout kết nối TCP
UDP_BROADCAST_PORT = 55100      # Port cho broadcast UDP
STATUS_BROADCAST_INTERVAL = 30  # Chu kỳ phát broadcast
```
- Định nghĩa **TẤT CẢ** các hằng số mạng trong hệ thống
- Tập trung cấu hình để dễ thay đổi và maintain
- Tránh hardcode giá trị trong code

**3. Tại sao cần tạo ở bước này?**
- ✅ **Cơ bản nhất:** Không phụ thuộc vào file nào khác
- ✅ **Độc lập hoàn toàn:** Pure Python, chỉ chứa constants
- ✅ **Nền tảng:** Mọi module networking sau này sẽ cần dùng
- ❌ **Không thể tạo muộn hơn:** Vì peer_listener, peer_client cần dùng ngay

**4. Được import/sử dụng bởi:**
- `Core/networking/peer_client.py` → Dùng `TCP_CONNECT_TIMEOUT`
- `Core/networking/peer_listener.py` → Dùng `TCP_BASE_PORT`
- `Core/routing/status_broadcaster.py` → Dùng `STATUS_BROADCAST_INTERVAL`
- Mọi module cần constants về network

---

### **BƯỚC 2: File Network Utilities**

#### 📄 File: `Core/utils/network_mode.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/utils/network_mode.py`
- **Loại:** Network utility functions
- **Dung lượng:** ~270 dòng code

**2. Chức năng chính trong bộ Core:**
```python
def get_local_ip() → str:
    # Lấy IP của máy trong LAN (VD: 192.168.1.10)
    # Bỏ qua adapter ảo (VirtualBox, Docker, VMware)

def get_broadcast_address() → str:
    # Tính địa chỉ broadcast (VD: 192.168.1.255)

def detect_network_mode() → str:
    # Phát hiện loại mạng: LAN, WiFi, Loopback
```
- **Tự động phát hiện IP** của máy trong mạng LAN
- **Lọc bỏ adapter ảo** để tránh lấy nhầm IP ảo
- **Tính toán broadcast address** cho UDP broadcast
- Xử lý cả Windows và Linux/Mac

**3. Tại sao cần tạo ở bước này?**
- ✅ **Chỉ phụ thuộc config.py:** Không phụ thuộc module phức tạp khác
- ✅ **Utility thuần túy:** Không có business logic
- ✅ **Cần thiết sớm:** Core API và StatusBroadcaster cần biết IP ngay khi khởi động
- ❌ **Không thể tạo muộn:** Vì router cần IP để gửi STATUS_UPDATE

**4. Được import/sử dụng bởi:**
- `Core/core_api.py` → Gọi `get_local_ip()` khi start()
- `Core/routing/status_broadcaster.py` → Dùng để gửi broadcast
- `Core/routing/message_router.py` → Lưu local_ip vào router
- Bất kỳ module nào cần biết IP của máy

---

### **BƯỚC 3: Data Models - Message**

#### 📄 File: `Core/models/message.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/models/message.py`
- **Loại:** Data model (dataclass)
- **Dung lượng:** ~180 dòng code

**2. Chức năng chính trong bộ Core:**
```python
@dataclass
class Message:
    message_id: str        # UUID duy nhất
    sender_id: str         # Peer ID người gửi
    receiver_id: str       # Peer ID người nhận
    msg_type: str          # "text", "file", "call_request", etc.
    content: str           # Nội dung tin nhắn
    timestamp: float       # Unix timestamp
    # ... các field optional
    
    @staticmethod
    def create_text(...) → Message
    def to_json() → str
    @classmethod
    def from_json(json_str) → Message
```
- **Định nghĩa cấu trúc tin nhắn** chuẩn trong toàn hệ thống
- **Factory methods** để tạo các loại message khác nhau:
  - `create_text()` - Tin nhắn văn bản
  - `create_file()` - Gửi file
  - `create_call_request()` - Yêu cầu cuộc gọi
  - `create_status_update()` - Cập nhật trạng thái
  - `create_friend_request()` - Lời mời kết bạn
- **Serialization:** `to_json()` và `from_json()` để truyền qua mạng

**3. Tại sao cần tạo ở bước này?**
- ✅ **Data model thuần túy:** Chỉ chứa data, không có logic phức tạp
- ✅ **Contract chung:** Mọi module giao tiếp qua Message object
- ✅ **Không phụ thuộc:** Chỉ dùng thư viện chuẩn (dataclasses, json, uuid)
- ❌ **Không thể tạo sau storage/networking:** Vì họ cần Message để hoạt động

**4. Được import/sử dụng bởi:**
- `Core/networking/peer_client.py` → Gửi Message qua TCP
- `Core/networking/peer_listener.py` → Nhận và parse Message
- `Core/routing/message_router.py` → Tạo và xử lý Message
- `Core/routing/message_handlers.py` → Xử lý từng loại Message
- `Core/storage/peer_message_storage.py` → Lưu Message vào JSON
- `Core/core_api.py` → Chuyển đổi Message ↔ dict
- **Tất cả modules** giao tiếp đều dùng Message

---

### **BƯỚC 4: Data Models - PeerInfo**

#### 📄 File: `Core/models/peer_info.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/models/peer_info.py`
- **Loại:** Data model (dataclass)
- **Dung lượng:** ~40 dòng code

**2. Chức năng chính trong bộ Core:**
```python
@dataclass
class PeerInfo:
    peer_id: str          # ID duy nhất của peer
    display_name: str     # Tên hiển thị
    ip: str              # Địa chỉ IP
    tcp_port: int        # Port TCP để kết nối
    status: str          # "online", "offline", "busy"
    last_seen: float     # Timestamp lần cuối thấy
    
    def to_dict() → Dict
    @classmethod
    def from_dict(data) → PeerInfo
```
- **Lưu trữ thông tin của một peer** (người dùng khác)
- **Tracking trạng thái:** online/offline/busy
- **Thông tin kết nối:** IP và Port để gửi tin nhắn
- **Serialization:** Lưu/đọc từ JSON

**3. Tại sao cần tạo ở bước này?**
- ✅ **Data model thuần túy:** Tương tự Message
- ✅ **Không phụ thuộc module khác:** Chỉ dùng dataclasses
- ✅ **Bổ sung cho Message:** Message chứa sender_id/receiver_id, PeerInfo chứa chi tiết peer
- ❌ **Không thể tạo sau routing:** Vì router cần PeerInfo để quản lý danh sách peers

**4. Được import/sử dụng bởi:**
- `Core/routing/message_router.py` → Lưu danh sách `Dict[str, PeerInfo]`
- `Core/routing/peer_manager.py` → Quản lý lifecycle của peers
- `Core/routing/message_handlers.py` → Tạo/cập nhật PeerInfo từ STATUS_UPDATE
- `Core/storage/data_manager.py` → Serialize PeerInfo vào peers.json
- `Core/core_api.py` → Chuyển PeerInfo → dict để gửi cho GUI

---

### **BƯỚC 5: Storage - Data Manager**

#### 📄 File: `Core/storage/data_manager.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/storage/data_manager.py`
- **Loại:** Storage utility
- **Dung lượng:** ~90 dòng code

**2. Chức năng chính trong bộ Core:**
```python
class DataManager:
    def __init__(self, username):
        self.user_dir = Path("data") / username
        
    def get_user_dir() → Path
    def get_profile_path() → Path
    def get_peers_file() → Path
    def get_peer_chat_dir(peer_id) → Path
    def get_peer_messages_file(peer_id) → Path
    def get_peer_files_dir(peer_id) → Path
    
    def save_file_for_peer(peer_id, file_name, file_bytes) → Path
    def load_peers() → Dict[str, PeerInfo]
    def save_peers(peers: Dict[str, PeerInfo])
```
- **Quản lý cấu trúc thư mục** của user:
  ```
  data/user_at_gmail.com/
  ├── profile.json
  ├── peers.json
  └── chats/
      └── {peer_id}/
          ├── messages.json
          └── files/
  ```
- **Tạo thư mục tự động** nếu chưa tồn tại
- **Đọc/ghi peers.json** - danh sách bạn bè
- **Lưu file đính kèm** vào folder riêng của từng peer

**3. Tại sao cần tạo ở bước này?**
- ✅ **Phụ thuộc Models:** Cần PeerInfo để serialize
- ✅ **Base cho storage:** PeerMessageStorage sẽ dùng DataManager
- ✅ **Không có business logic:** Chỉ quản lý file/folder
- ❌ **Không thể tạo sau networking:** Router cần load peers ngay khi khởi động

**4. Được import/sử dụng bởi:**
- `Core/storage/peer_message_storage.py` → Dùng để lấy đường dẫn messages.json
- `Core/routing/message_router.py` → Khởi tạo DataManager, load/save peers
- `Core/routing/message_handlers.py` → Lưu file đính kèm
- `Core/core_api.py` → Truy cập files_dir để kiểm tra file tồn tại

---

### **BƯỚC 6: Storage - Peer Message Storage**

#### 📄 File: `Core/storage/peer_message_storage.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/storage/peer_message_storage.py`
- **Loại:** Message persistence layer
- **Dung lượng:** ~60 dòng code

**2. Chức năng chính trong bộ Core:**
```python
class PeerMessageStorage:
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        
    def save_message(peer_id: str, message: Message):
        # Lưu message vào chats/{peer_id}/messages.json
        
    def load_messages(peer_id: str) → List[Message]:
        # Load tất cả tin nhắn với peer_id
        
    def get_last_message(peer_id: str) → Optional[Message]:
        # Lấy tin nhắn cuối cùng (dùng cho preview)
```
- **Lưu trữ lịch sử chat** với từng peer riêng biệt
- **Mỗi peer một file JSON:** `chats/{peer_id}/messages.json`
- **Append-only:** Mỗi tin nhắn mới được append vào cuối file
- **Load theo peer:** Không load hết, chỉ load khi cần

**3. Tại sao cần tạo ở bước này?**
- ✅ **Phụ thuộc DataManager và Message:** Cần cả 2 để hoạt động
- ✅ **Trước routing:** Router cần save/load messages khi gửi/nhận
- ✅ **Tách riêng persistence logic:** Không để router xử lý file I/O
- ❌ **Không thể tạo sau router:** Router cần PeerMessageStorage ngay khi init

**4. Được import/sử dụng bởi:**
- `Core/routing/message_router.py` → Khởi tạo và sử dụng để save/load messages
- `Core/routing/message_handlers.py` → Gọi save_message() khi nhận tin nhắn
- `Core/core_api.py` → Gọi get_message_history() để load cho GUI

---

### **BƯỚC 7: Networking - Peer Client (TCP Sender)**

#### 📄 File: `Core/networking/peer_client.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/networking/peer_client.py`
- **Loại:** TCP client
- **Dung lượng:** ~25 dòng code (rất đơn giản)

**2. Chức năng chính trong bộ Core:**
```python
class PeerClient:
    def send(self, peer_ip: str, peer_port: int, message: Message) → bool:
        payload = message.to_json() + "\n"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(config.TCP_CONNECT_TIMEOUT)
            sock.connect((peer_ip, peer_port))
            sock.sendall(payload.encode("utf-8"))
            return True
```
- **Gửi Message qua TCP** đến peer
- **Blocking call:** Connect → Send → Close
- **Format:** JSON + newline delimiter (`\n`)
- **Error handling:** Return False nếu peer offline

**3. Tại sao cần tạo ở bước này?**
- ✅ **Phụ thuộc Message và config:** Cần Message.to_json() và TCP_CONNECT_TIMEOUT
- ✅ **Đơn giản nhất trong networking:** Chỉ gửi, không nhận
- ✅ **Stateless:** Không giữ kết nối, mỗi lần gửi tạo socket mới
- ❌ **Không thể tạo sau router:** Router cần PeerClient để gửi tin nhắn

**4. Được import/sử dụng bởi:**
- `Core/routing/message_router.py` → Dùng để gửi mọi loại message
- `Core/routing/friend_request_manager.py` → Gửi friend request/accept/reject
- `Core/routing/status_broadcaster.py` → Gửi STATUS_UPDATE
- `Core/core_api.py` → Gửi CALL_REQUEST, CALL_ACCEPT, etc.

---

### **BƯỚC 8: Networking - Peer Listener (TCP Server)**

#### 📄 File: `Core/networking/peer_listener.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/networking/peer_listener.py`
- **Loại:** TCP server (multi-threaded)
- **Dung lượng:** ~193 dòng code

**2. Chức năng chính trong bộ Core:**
```python
class PeerListener:
    def __init__(self, tcp_port: int, on_message_callback):
        self.tcp_port = tcp_port
        self.on_message_callback = on_message_callback
        
    def start():
        # Bind socket vào 0.0.0.0:tcp_port
        # Accept loop trong thread riêng
        
    def _accept_loop():
        while running:
            client_socket, address = server_socket.accept()
            # Tạo thread mới cho mỗi connection
            threading.Thread(target=_handle_client)
            
    def _handle_client(client_socket, client_address):
        # Đọc JSON từ socket
        # Parse thành Message
        # Gọi callback với Message và IP
```
- **Lắng nghe kết nối TCP** từ peers khác
- **Multi-threaded:** Mỗi connection một thread
- **Parse Message:** Đọc JSON và convert thành Message object
- **Callback pattern:** Gọi callback để router xử lý message

**3. Tại sao cần tạo ở bước này?**
- ✅ **Phụ thuộc Message và config:** Cần Message.from_json() và TCP_BASE_PORT
- ✅ **Đối xứng với PeerClient:** Client gửi → Server nhận
- ✅ **Threading riêng:** Không block main thread
- ❌ **Không thể tạo sau router:** Router cần PeerListener để nhận tin nhắn

**4. Được import/sử dụng bởi:**
- `Core/routing/message_router.py` → Khởi tạo PeerListener khi connect_core()
- Callback sẽ được router set để xử lý tin nhắn đến
- Đây là **entry point** của mọi tin nhắn đến trong hệ thống P2P

---

### **BƯỚC 9: Networking - UDP Stream**

#### 📄 File: `Core/networking/udp_stream.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/networking/udp_stream.py`
- **Loại:** UDP sender & receiver
- **Dung lượng:** ~117 dòng code

**2. Chức năng chính trong bộ Core:**
```python
class UDPSender:
    def send_audio(audio_bytes, peer_ip, peer_port):
        # Gửi audio chunk qua UDP
        # Format: b"AUDIO:" + audio_bytes
        
    def send_video(video_bytes, peer_ip, peer_port):
        # Gửi video frame qua UDP
        # Format: b"VIDEO:" + video_bytes

class UDPReceiver:
    def __init__(self, audio_port, video_port, on_audio_callback, on_video_callback):
        # Tạo 2 sockets: audio + video
        
    def start():
        # 2 threads: _receive_audio_loop() và _receive_video_loop()
        
    def _receive_audio_loop():
        while running:
            data, addr = audio_socket.recvfrom(65535)
            if data.startswith(b"AUDIO:"):
                on_audio_callback(data[6:])
```
- **Gửi/nhận audio/video qua UDP** (không qua TCP vì cần real-time)
- **2 ports riêng:** Audio port và Video port
- **Prefix protocol:** "AUDIO:" hoặc "VIDEO:" để phân biệt
- **Fire-and-forget:** UDP không đảm bảo, nhưng nhanh

**3. Tại sao cần tạo ở bước này?**
- ✅ **Độc lập với TCP:** Dùng cho streaming, không dùng cho messaging
- ✅ **Không phụ thuộc models:** Chỉ gửi raw bytes
- ✅ **Cần trước media:** AudioStream và VideoStream sẽ dùng UDPSender/Receiver
- ❌ **Không thể tạo sau media:** Media modules cần UDP để hoạt động

**4. Được import/sử dụng bởi:**
- `Core/media/audio_stream.py` → AudioCapture dùng UDPSender, AudioPlayback dùng UDPReceiver
- `Core/media/video_stream.py` → VideoCapture dùng UDPSender, VideoDecoder dùng UDPReceiver
- `Core/call/call_manager.py` → Khởi tạo UDPSender/Receiver cho call

---

### **BƯỚC 10: Media - Audio Stream**

#### 📄 File: `Core/media/audio_stream.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/media/audio_stream.py`
- **Loại:** Audio capture & playback
- **Dung lượng:** ~150 dòng code

**2. Chức năng chính trong bộ Core:**
```python
class AudioCapture:
    def __init__(self, udp_sender, peer_ip, peer_port):
        # PyAudio config: 16kHz, mono, 16-bit
        
    def start():
        # Mở mic stream
        # Thread chạy _capture_loop()
        
    def _capture_loop():
        while running:
            audio_chunk = stream.read(1024)  # Đọc từ mic
            if not muted:
                udp_sender.send_audio(audio_chunk, peer_ip, peer_port)

class AudioPlayback:
    def __init__(self):
        self.audio_queue = queue.Queue()
        
    def start():
        # Mở speaker stream
        # Thread chạy _playback_loop()
        
    def _playback_loop():
        while running:
            audio_data = self.audio_queue.get()  # Lấy từ queue
            stream.write(audio_data)  # Phát ra loa
            
    def put_audio_data(audio_bytes):
        # UDPReceiver callback gọi hàm này
        self.audio_queue.put(audio_bytes)
```
- **AudioCapture:** Thu âm từ mic → Gửi qua UDP
- **AudioPlayback:** Nhận từ UDP → Phát ra loa
- **Queue buffer:** Tránh bị mất gói do timing
- **Mute/Unmute:** Toggle microphone

**3. Tại sao cần tạo ở bước này?**
- ✅ **Phụ thuộc UDPStream:** Cần UDPSender để gửi audio
- ✅ **Độc lập với video:** Audio và Video có thể tách riêng
- ✅ **Trước CallManager:** CallManager sẽ khởi tạo AudioCapture/Playback
- ❌ **Không thể tạo sau CallManager:** CallManager cần audio để hoạt động

**4. Được import/sử dụng bởi:**
- `Core/call/call_manager.py` → Khởi tạo AudioCapture và AudioPlayback khi bắt đầu call
- CallManager điều khiển start/stop/toggle_mute

---

### **BƯỚC 11: Media - Video Stream**

#### 📄 File: `Core/media/video_stream.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/media/video_stream.py`
- **Loại:** Video capture & decode
- **Dung lượng:** ~180 dòng code

**2. Chức năng chính trong bộ Core:**
```python
class VideoCapture:
    def __init__(self, udp_sender, peer_ip, peer_port):
        # OpenCV config: 640x480, 15 FPS
        
    def start():
        # Mở webcam (cv2.VideoCapture)
        # Thread chạy _capture_loop()
        
    def _capture_loop():
        while running:
            ret, frame = webcam.read()
            frame = cv2.resize(frame, (640, 480))
            _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if not camera_off:
                udp_sender.send_video(jpeg.tobytes(), peer_ip, peer_port)
            time.sleep(1/15)  # 15 FPS

class VideoDecoder:
    def __init__(self, on_frame_callback):
        self.video_queue = queue.Queue()
        self.on_frame_callback = on_frame_callback
        
    def start():
        # Thread chạy _decode_loop()
        
    def _decode_loop():
        while running:
            jpeg_data = self.video_queue.get()
            frame = cv2.imdecode(np.frombuffer(jpeg_data, np.uint8), cv2.IMREAD_COLOR)
            self.on_frame_callback(frame)  # Gửi frame cho GUI
            
    def put_video_data(video_bytes):
        # UDPReceiver callback gọi hàm này
        self.video_queue.put(video_bytes)
```
- **VideoCapture:** Thu video từ webcam → Encode JPEG → Gửi qua UDP
- **VideoDecoder:** Nhận JPEG từ UDP → Decode → Gọi callback để GUI hiển thị
- **Compression:** JPEG quality 70% để giảm bandwidth
- **Frame rate:** 15 FPS (cân bằng giữa chất lượng và bandwidth)

**3. Tại sao cần tạo ở bước này?**
- ✅ **Phụ thuộc UDPStream:** Tương tự AudioStream
- ✅ **Tách riêng với audio:** Voice call không cần video
- ✅ **Trước CallManager:** CallManager sẽ khởi tạo nếu là video call
- ❌ **Không thể tạo sau CallManager:** CallManager cần video để hoạt động

**4. Được import/sử dụng bởi:**
- `Core/call/call_manager.py` → Khởi tạo VideoCapture và VideoDecoder cho video call
- CallManager điều khiển start/stop/toggle_camera

---

### **BƯỚC 12: Routing - Peer Manager**

#### 📄 File: `Core/routing/peer_manager.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/routing/peer_manager.py`
- **Loại:** Peer lifecycle manager
- **Dung lượng:** ~30 dòng code

**2. Chức năng chính trong bộ Core:**
```python
class PeerManager:
    def __init__(self, router):
        self.router = router
        
    def get_known_peers() → List[PeerInfo]:
        # Lấy list tất cả peers từ router._peers
        
    def cleanup_offline_peers(max_offline_time) → int:
        # Xóa peers offline quá lâu (hiện chưa implement)
        
    def notify_existing_peers():
        # Duyệt tất cả peers
        # Gọi peer_callback để GUI refresh
```
- **Quản lý danh sách peers** trong router
- **Truy vấn peers:** Cung cấp interface để lấy danh sách
- **Cleanup:** Dọn dẹp peers offline (optional)
- **Notification:** Thông báo GUI về peers hiện có

**3. Tại sao cần tạo ở bước này?**
- ✅ **Phụ thuộc PeerInfo:** Cần PeerInfo model
- ✅ **Helper cho router:** Tách logic quản lý peers khỏi router
- ✅ **Không phụ thuộc networking:** Chỉ quản lý data structure
- ⚠️ **Có thể tạo cùng router:** Nhưng tách riêng cho clean architecture

**4. Được import/sử dụng bởi:**
- `Core/routing/message_router.py` → Khởi tạo PeerManager làm sub-component
- Router delegate các thao tác quản lý peers cho PeerManager

---

### **BƯỚC 13: Routing - Friend Request Manager**

#### 📄 File: `Core/routing/friend_request_manager.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/routing/friend_request_manager.py`
- **Loại:** Friend request handler
- **Dung lượng:** ~40 dòng code

**2. Chức năng chính trong bộ Core:**
```python
class FriendRequestManager:
    def __init__(self, router):
        self.router = router
        
    def send_friend_request(peer_id) → bool:
        # Tạo Message.create_friend_request()
        # Gửi qua PeerClient
        
    def send_friend_accept(peer_id) → bool:
        # Tạo Message.create_friend_accept()
        # Gửi qua PeerClient
        # Đánh dấu peer là "accepted"
        
    def send_friend_reject(peer_id) → bool:
        # Tạo Message.create_friend_reject()
        # Gửi qua PeerClient
```
- **Xử lý logic friend request** (lời mời kết bạn)
- **3 actions:** Send request, Accept, Reject
- **Update status:** Đánh dấu peer là bạn bè sau khi accept
- **Encapsulate logic:** Tách khỏi router để dễ maintain

**3. Tại sao cần tạo ở bước này?**
- ✅ **Phụ thuộc Message và PeerClient:** Cần cả 2 để gửi message
- ✅ **Tách logic nghiệp vụ:** Không để router xử lý trực tiếp friend request
- ✅ **Trước router:** Router sẽ delegate friend request cho manager này
- ⚠️ **Có thể tạo sau router:** Nhưng tạo trước cho đúng dependency order

**4. Được import/sử dụng bởi:**
- `Core/routing/message_router.py` → Khởi tạo và sử dụng FriendRequestManager
- Router gọi các methods khi GUI request add/accept/reject friend

---

### **BƯỚC 14: Routing - Status Broadcaster**

#### 📄 File: `Core/routing/status_broadcaster.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/routing/status_broadcaster.py`
- **Loại:** Background status updater
- **Dung lượng:** ~70 dòng code

**2. Chức năng chính trong bộ Core:**
```python
class StatusBroadcaster:
    def __init__(self, router):
        self.router = router
        self.interval = 30  # giây
        
    def start():
        # Thread chạy _broadcast_loop()
        
    def _broadcast_loop():
        while running:
            time.sleep(30)
            self.send_status_to_all_peers("online")
            
    def send_status_to_all_peers(status):
        # Duyệt tất cả peers
        for peer in router._peers.values():
            message = Message.create_status_update(status)
            peer_client.send(peer.ip, peer.tcp_port, message)
            
    def send_status_to_peer(peer_id, status):
        # Gửi status đến 1 peer cụ thể
```
- **Phát trạng thái định kỳ** (30 giây/lần) đến tất cả peers
- **Keep-alive:** Cho peers biết mình vẫn online
- **Graceful shutdown:** Gửi "offline" trước khi thoát app
- **Background thread:** Không block main thread

**3. Tại sao cần tạo ở bước này?**
- ✅ **Phụ thuộc Message và PeerClient:** Cần gửi STATUS_UPDATE message
- ✅ **Phụ thuộc router:** Cần truy cập danh sách peers
- ✅ **Trước router:** Router sẽ khởi động broadcaster khi start
- ❌ **Không thể tạo sau router:** Router cần broadcaster để maintain status

**4. Được import/sử dụng bởi:**
- `Core/routing/message_router.py` → Khởi tạo StatusBroadcaster khi connect_core()
- Router gọi start() và stop() để điều khiển broadcaster

---

### **BƯỚC 15: Routing - Message Handlers**

#### 📄 File: `Core/routing/message_handlers.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/routing/message_handlers.py`
- **Loại:** Message type dispatcher
- **Dung lượng:** ~250 dòng code

**2. Chức năng chính trong bộ Core:**
```python
class MessageHandlers:
    def __init__(self, router):
        self.router = router
        
    def handle_incoming_message(message: Message, sender_ip: str):
        # Dispatcher: Kiểm tra msg_type và gọi handler tương ứng
        if message.msg_type == "text":
            self._handle_text_message(message, sender_ip)
        elif message.msg_type == "file":
            self._handle_file_message(message, sender_ip)
        elif message.msg_type == "status_update":
            self._handle_status_update(message, sender_ip)
        elif message.msg_type == "friend_request":
            self._handle_friend_request(message, sender_ip)
        # ... và nhiều handlers khác
        
    def _handle_text_message(message, sender_ip):
        # Lưu vào storage
        # Gọi callback để GUI hiển thị
        
    def _handle_status_update(message, sender_ip):
        # Cập nhật hoặc tạo peer mới
        # Update IP, port, status, last_seen
        # Save peers.json
        # Gọi peer_callback
        
    def _handle_call_request(message, sender_ip):
        # Parse call_type, audio_port, video_port
        # Gọi call_request_callback → GUI hiện CallDialog
```
- **Central dispatcher** cho tất cả tin nhắn đến
- **Handler cho mỗi msg_type:**
  - text, file, image, audio
  - status_update
  - friend_request, friend_accept, friend_reject
  - call_request, call_accept, call_reject, call_end
  - unfriend
- **Side effects:** Lưu storage, cập nhật peers, gọi callbacks
- **Tạo peer từ STATUS_UPDATE:** Peer mới có thể tự giới thiệu qua STATUS_UPDATE

**3. Tại sao cần tạo ở bước này?**
- ✅ **Phụ thuộc tất cả components trước đó:**
  - Message, PeerInfo (models)
  - DataManager, PeerMessageStorage (storage)
  - PeerClient (để reply)
- ✅ **Tách logic phức tạp:** Không để router xử lý hết
- ✅ **Trước router:** Router sẽ delegate message handling cho class này
- ❌ **Không thể tạo sau router:** Router cần handlers để xử lý tin nhắn đến

**4. Được import/sử dụng bởi:**
- `Core/routing/message_router.py` → Khởi tạo MessageHandlers
- PeerListener callback gọi `message_handlers.handle_incoming_message()`

---

### **BƯỚC 16: Routing - Message Router (CORE CENTRAL)**

#### 📄 File: `Core/routing/message_router.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/routing/message_router.py`
- **Loại:** **Central coordinator** của toàn bộ hệ thống P2P
- **Dung lượng:** ~360 dòng code

**2. Chức năng chính trong bộ Core:**
```python
class MessageRouter:
    def __init__(self):
        self.peer_id = str(uuid.uuid4())[:8]  # ID của mình
        self._peers: Dict[str, PeerInfo] = {}  # Danh sách peers
        self._lock = threading.Lock()  # Thread safety
        
        # Khởi tạo sub-components
        self.peer_manager = PeerManager(self)
        self.friend_request_manager = FriendRequestManager(self)
        self.message_handlers = MessageHandlers(self)
        
    def connect_core(self, username, display_name, tcp_port, on_message_callback):
        # Khởi tạo storage
        self.data_manager = DataManager(username)
        self.peer_message_storage = PeerMessageStorage(self.data_manager)
        
        # Khởi tạo networking
        self.peer_client = PeerClient()
        self.peer_listener = PeerListener(tcp_port, self._on_tcp_message)
        self.status_broadcaster = StatusBroadcaster(self)
        
        # Load peers từ JSON
        self._peers = self.data_manager.load_peers()
        
        # Start services
        self.peer_listener.start()
        self.status_broadcaster.start()
        
    def send_message(peer_id, content, msg_type, ...) → (bool, Message):
        # Tạo Message object
        # Gửi qua peer_client
        # Lưu vào storage
        
    def add_peer_by_ip(ip, port, display_name) → (bool, str):
        # Tạo peer_id mới
        # Tạo PeerInfo
        # Gửi STATUS_UPDATE để giới thiệu
        # Gửi FRIEND_REQUEST
        # Lưu vào _peers và peers.json
        
    def get_known_peers() → List[PeerInfo]
    def get_message_history(peer_id) → List[Message]
    
    def send_friend_request(peer_id) → bool
    def send_friend_accept(peer_id) → bool
    def send_friend_reject(peer_id) → bool
    
    def stop():
        # Gửi offline status
        # Dừng listener và broadcaster
        
    def _on_tcp_message(message, sender_ip):
        # Callback từ PeerListener
        # Delegate cho message_handlers
```
- **Trung tâm điều phối** của hệ thống P2P:
  - Quản lý danh sách peers
  - Gửi/nhận tin nhắn
  - Điều phối các sub-components
- **Aggregate root:** Tích hợp tất cả components:
  - Storage (DataManager, PeerMessageStorage)
  - Networking (PeerClient, PeerListener)
  - Sub-managers (PeerManager, FriendRequestManager, StatusBroadcaster)
  - Handlers (MessageHandlers)
- **Lifecycle management:** Start/stop các services
- **Thread-safe:** Sử dụng lock để bảo vệ `_peers` dict

**3. Tại sao cần tạo ở bước này?**
- ✅ **Phụ thuộc TẤT CẢ components trước đó:**
  - Models: Message, PeerInfo
  - Storage: DataManager, PeerMessageStorage
  - Networking: PeerClient, PeerListener
  - Routing: PeerManager, FriendRequestManager, StatusBroadcaster, MessageHandlers
- ✅ **Core của core:** Là trung tâm kết nối tất cả
- ✅ **Trước Core API:** Core API sẽ wrap MessageRouter
- ❌ **KHÔNG THỂ TẠO SỚM HƠN:** Vì cần tất cả dependencies đã có sẵn

**4. Được import/sử dụng bởi:**
- `Core/core_api.py` → Khởi tạo MessageRouter làm thành phần chính
- `Core/__init__.py` → Export MessageRouter ra ngoài
- Đây là **tim của hệ thống P2P**

---

### **BƯỚC 17: Call - Call Manager**

#### 📄 File: `Core/call/call_manager.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/call/call_manager.py`
- **Loại:** Call orchestrator
- **Dung lượng:** ~280 dòng code

**2. Chức năng chính trong bộ Core:**
```python
class CallState(Enum):
    IDLE = "idle"
    OUTGOING = "outgoing"
    INCOMING = "incoming"
    CONNECTED = "connected"

class CallType(Enum):
    VOICE = "voice"
    VIDEO = "video"

class CallManager:
    def __init__(self):
        self.state = CallState.IDLE
        self.call_type = None
        
        # Media components (khởi tạo khi cần)
        self.audio_capture = None
        self.audio_playback = None
        self.video_capture = None
        self.video_decoder = None
        
        # UDP components
        self.udp_sender = None
        self.udp_receiver = None
        
    def start_outgoing_call(peer_id, peer_name, peer_ip, call_type) → (bool, int, int):
        # Cấp phát audio_port, video_port
        # Khởi tạo UDPReceiver
        # Set state = OUTGOING
        # Return ports để gửi trong CALL_REQUEST
        
    def prepare_incoming_call(...) → bool:
        # Lưu thông tin peer và ports
        # Set state = INCOMING
        
    def accept_incoming_call() → (bool, int, int):
        # Cấp phát ports của mình
        # Return để gửi trong CALL_ACCEPT
        
    def start_media_streams(peer_audio_port, peer_video_port) → bool:
        # Khởi tạo AudioCapture, AudioPlayback
        # Nếu VIDEO: Khởi tạo VideoCapture, VideoDecoder
        # Khởi tạo UDPSender
        # Start tất cả streams
        # Set state = CONNECTED
        
    def end_call():
        # Dừng tất cả streams
        # Đóng sockets
        # Set state = IDLE
        
    def toggle_mute():
        if self.audio_capture:
            self.audio_capture.toggle_mute()
            
    def toggle_camera():
        if self.video_capture:
            self.video_capture.toggle_camera()
```
- **Điều phối cuộc gọi video/audio:**
  - State machine: IDLE → OUTGOING/INCOMING → CONNECTED → IDLE
  - Quản lý lifecycle của media streams
  - Phân phối ports cho UDP
- **Orchestrate media components:**
  - AudioCapture + AudioPlayback
  - VideoCapture + VideoDecoder (nếu video call)
  - UDPSender + UDPReceiver
- **Control APIs:** Mute/Unmute, Camera On/Off
- **Callbacks:** Thông báo state change, video frames, errors

**3. Tại sao cần tạo ở bước này?**
- ✅ **Phụ thuộc tất cả media + networking:**
  - Media: AudioStream, VideoStream
  - Networking: UDPStream
- ✅ **High-level orchestrator:** Kết hợp nhiều components phức tạp
- ✅ **Trước Core API:** Core API sẽ sử dụng CallManager
- ❌ **Không thể tạo sớm hơn:** Vì cần media components đã sẵn sàng

**4. Được import/sử dụng bởi:**
- `Core/core_api.py` → Khởi tạo CallManager trong ChatCore
- Core API gọi start_call(), accept_call(), end_call()
- GUI điều khiển cuộc gọi thông qua Core API

---

### **BƯỚC 18: Core API (PUBLIC INTERFACE)**

#### 📄 File: `Core/core_api.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/core_api.py`
- **Loại:** **Public API** - Giao diện duy nhất giữa Core và GUI
- **Dung lượng:** ~390 dòng code

**2. Chức năng chính trong bộ Core:**
```python
class CoreSignals(QObject):
    # Qt Signals để gửi events lên GUI
    message_received = Signal(dict)
    peer_updated = Signal(dict)
    friend_request_received = Signal(str, str)
    friend_accepted = Signal(str)
    friend_rejected = Signal(str)
    call_request_received = Signal(str, str, str)
    call_accepted = Signal(str)
    call_rejected = Signal(str)
    call_ended = Signal(str)
    remote_video_frame = Signal(bytes)

class ChatCore:
    def __init__(self, username, display_name, tcp_port):
        self.signals = CoreSignals()
        self.router = MessageRouter()
        self.call_manager = CallManager()
        
    # === Lifecycle ===
    def start():
        # Khởi động router
        # Khởi động call manager callbacks
        # Lấy local IP
        
    def stop():
        # Dừng router
        
    # === Messaging ===
    def send_message(peer_id, content, msg_type, ...) → bool
    def get_known_peers() → List[Dict]
    def get_message_history(peer_id) → List[Dict]
    
    # === Friend Management ===
    def add_peer_by_ip(ip, port, display_name) → (bool, str)
    def send_friend_request(peer_id) → bool
    def accept_friend(peer_id) → bool
    def reject_friend(peer_id) → bool
    
    # === Call Management ===
    def start_call(peer_id, call_type) → bool
    def accept_call(peer_id) → bool
    def reject_call(peer_id) → bool
    def end_call() → bool
    
    # === Internal Handlers (private) ===
    def _handle_router_message(message):
        # Convert Message → dict
        # Emit signal message_received
        
    def _handle_peer_update(peer_info):
        # Convert PeerInfo → dict
        # Emit signal peer_updated
        
    def _handle_friend_request(peer_id, display_name):
        # Emit signal friend_request_received
        
    def _handle_call_request(...):
        # Emit signal call_request_received
        
    # ... nhiều handlers khác
```
- **Facade pattern:** Che giấu complexity của Core, chỉ expose API đơn giản
- **DTO conversion:** Convert Core objects (Message, PeerInfo) → dict để GUI dùng
- **Signal-based:** Dùng Qt Signals để async communication với GUI
- **Single entry point:** GUI chỉ cần biết ChatCore, không cần biết Router/CallManager/...
- **Separation of concerns:** Core không biết gì về GUI, GUI không biết gì về Core internals

**3. Tại sao cần tạo ở bước này (cuối cùng)?**
- ✅ **Phụ thuộc TẤT CẢ Core components:**
  - MessageRouter (toàn bộ routing)
  - CallManager (toàn bộ call)
  - Models (để convert)
- ✅ **API layer:** Wrap tất cả functionality
- ✅ **Cuối cùng:** Vì là "mặt tiền" của Core, cần tất cả backend đã sẵn sàng
- ❌ **KHÔNG THỂ TẠO SỚM:** Vì cần Router và CallManager hoàn chỉnh

**4. Được import/sử dụng bởi:**
- `Gui/controller/main_window_controller.py` → Khởi tạo ChatCore
- `Core/__init__.py` → Export ChatCore ra ngoài
- GUI **CHỈ** tương tác với ChatCore, không bao giờ import Router/Storage/Networking trực tiếp
- **Đây là PUBLIC API duy nhất của Core module**

---

### **BƯỚC 19: Core Package Export**

#### 📄 File: `Core/__init__.py`

**1. File này là gì?**
- **Đường dẫn:** `Core/__init__.py`
- **Loại:** Package initialization
- **Dung lượng:** ~5 dòng code

**2. Chức năng chính trong bộ Core:**
```python
from Core.routing.message_router import MessageRouter
from Core.core_api import ChatCore

__all__ = ["MessageRouter", "ChatCore"]
```
- **Export public APIs:**
  - `ChatCore` - API chính cho GUI
  - `MessageRouter` - Cho advanced usage (nếu cần)
- **Package interface:** Define cái gì có thể import từ `Core`
- **Clean imports:** GUI có thể `from Core import ChatCore`

**3. Tại sao cần tạo ở bước này?**
- ✅ **Cuối cùng:** Sau khi tất cả modules đã hoàn thành
- ✅ **Package convention:** Python best practice
- ✅ **Không phụ thuộc gì:** Chỉ import và re-export
- ⚠️ **Có thể tạo đầu tiên:** Nhưng nội dung phải cập nhật cuối cùng

**4. Được import/sử dụng bởi:**
- `main.py` - Có thể import: `from Core import ChatCore`
- `Gui/controller/` - Import ChatCore từ Core
- Bất kỳ module nào ngoài Core muốn dùng Core

---

## 📊 SƠ ĐỒ DEPENDENCY (THỨ TỰ TẠO FILE)

```
1. config.py                    (Không phụ thuộc gì)
2. network_mode.py              ↑ config
3. message.py                   (Không phụ thuộc Core)
4. peer_info.py                 (Không phụ thuộc Core)
5. data_manager.py              ↑ peer_info
6. peer_message_storage.py     ↑ data_manager, message
7. peer_client.py               ↑ message, config
8. peer_listener.py             ↑ message, config
9. udp_stream.py                (Không phụ thuộc Core)
10. audio_stream.py             ↑ udp_stream
11. video_stream.py             ↑ udp_stream
12. peer_manager.py             ↑ peer_info
13. friend_request_manager.py  ↑ message, peer_client
14. status_broadcaster.py      ↑ message, peer_client
15. message_handlers.py        ↑ message, peer_info, data_manager, peer_message_storage, peer_client
16. message_router.py          ↑ TẤT CẢ routing components + storage + networking
17. call_manager.py            ↑ audio_stream, video_stream, udp_stream
18. core_api.py                ↑ message_router, call_manager
19. __init__.py                ↑ core_api, message_router
```

---

## 🎯 LUỒNG XỬ LÝ CHÍNH

### **Luồng khởi động Core:**
```
ChatCore.start()
    → MessageRouter.connect_core()
        → DataManager.__init__()
        → PeerMessageStorage.__init__()
        → PeerClient.__init__()
        → PeerListener.start() ─┐ (Thread 1: Accept loop)
        → StatusBroadcaster.start() ─┐ (Thread 2: Broadcast loop)
        → Load peers từ JSON
        → Gửi STATUS_UPDATE đến tất cả peers
```

### **Luồng gửi tin nhắn:**
```
GUI → ChatCore.send_message()
    → MessageRouter.send_message()
        → Message.create_text()
        → PeerClient.send(peer_ip, peer_port, message)
            → TCP socket connect
            → Send JSON
        → PeerMessageStorage.save_message()
            → Append vào messages.json
```

### **Luồng nhận tin nhắn:**
```
TCP packet arrives
    → PeerListener._handle_client()
        → Parse JSON → Message object
        → Callback: router._on_tcp_message()
            → MessageHandlers.handle_incoming_message()
                → _handle_text_message()
                    → PeerMessageStorage.save_message()
                    → Callback: ChatCore._handle_router_message()
                        → Convert Message → dict
                        → Signal: message_received.emit(dict)
                            → GUI nhận signal
                            → Hiển thị MessageBubble
```

### **Luồng video call:**
```
GUI click "Video Call"
    → ChatCore.start_call(peer_id, "video")
        → CallManager.start_outgoing_call()
            → Cấp phát audio_port, video_port
            → Khởi tạo UDPReceiver
        → Message.create_call_request(audio_port, video_port)
        → PeerClient.send(CALL_REQUEST)
        
Peer nhận CALL_REQUEST
    → MessageHandlers._handle_call_request()
        → ChatCore._handle_call_request()
            → Signal: call_request_received.emit()
                → GUI hiển thị CallDialog
                
User click "Accept"
    → ChatCore.accept_call()
        → CallManager.accept_incoming_call()
            → Cấp phát ports của mình
        → Message.create_call_accept(my_ports)
        → PeerClient.send(CALL_ACCEPT)
        → CallManager.start_media_streams()
            → AudioCapture.start() ─┐ (Thread: Capture audio)
            → AudioPlayback.start() ─┐ (Thread: Play audio)
            → VideoCapture.start() ─┐ (Thread: Capture video)
            → UDPSender: Gửi audio/video
            → UDPReceiver: Nhận audio/video ─┐ (2 Threads)
            
Audio/Video streaming
    AudioCapture._capture_loop()
        → Read from mic
        → UDPSender.send_audio(bytes)
    
    UDPReceiver._receive_audio_loop()
        → Receive UDP packet
        → AudioPlayback.put_audio_data(bytes)
            → AudioPlayback._playback_loop()
                → Write to speaker
```

---

## ✅ CHECKLIST XÂY DỰNG CORE (THEO THỨ TỰ)

- [x] **Bước 1-2:** Utils (config, network_mode)
- [x] **Bước 3-4:** Models (message, peer_info)
- [x] **Bước 5-6:** Storage (data_manager, peer_message_storage)
- [x] **Bước 7-9:** Networking (peer_client, peer_listener, udp_stream)
- [x] **Bước 10-11:** Media (audio_stream, video_stream)
- [x] **Bước 12-15:** Routing sub-components (peer_manager, friend_request_manager, status_broadcaster, message_handlers)
- [x] **Bước 16:** Routing core (message_router) - **TRUNG TÂM**
- [x] **Bước 17:** Call (call_manager)
- [x] **Bước 18:** Core API (core_api) - **PUBLIC INTERFACE**
- [x] **Bước 19:** Package export (__init__.py)

---

## 🎓 NGUYÊN TẮC THIẾT KẾ

### **1. Separation of Concerns**
- Mỗi module có 1 trách nhiệm duy nhất
- Utils → Models → Storage → Networking → Media → Routing → API

### **2. Dependency Inversion**
- High-level modules (Core API) không phụ thuộc low-level (Networking)
- Cả 2 phụ thuộc abstractions (Message, PeerInfo)

### **3. Layered Architecture**
```
API Layer:        core_api.py
Business Logic:   routing/, call/
Services:         media/, networking/
Data:             storage/, models/
Utilities:        utils/
```

### **4. Single Entry Point**
- GUI chỉ import `ChatCore`
- Core internal modules không expose ra ngoài

### **5. Async Communication**
- Sử dụng Qt Signals để non-blocking
- Threading cho I/O operations
- Callbacks cho event handling

---

## 🚀 KẾT LUẬN

Thư mục `/Core` được xây dựng theo chiến lược **Bottom-Up** với dependency rõ ràng:

1. **Foundation:** Utils và Models không phụ thuộc gì
2. **Infrastructure:** Storage và Networking phụ thuộc Models
3. **Services:** Media và Routing phụ thuộc Infrastructure
4. **Integration:** Call Manager tích hợp Media
5. **API:** Core API wrap tất cả, là entry point duy nhất

**Thứ tự này đảm bảo:**
- ✅ Không có circular dependencies
- ✅ Mỗi bước build lên từ bước trước
- ✅ Test được từng layer riêng biệt
- ✅ Dễ maintain và mở rộng

**GUI chỉ cần biết:** `from Core import ChatCore` và sử dụng API của nó! 🎉

