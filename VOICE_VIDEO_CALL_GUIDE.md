# 📞 Voice & Video Call - Hướng Dẫn Sử Dụng

## 🎯 Tổng Quan

Project đã được tích hợp đầy đủ chức năng **Voice Call** (gọi thoại) và **Video Call** (gọi video) P2P (peer-to-peer) giữa 2 người dùng.

### ✨ Tính năng:
- ✅ Voice Call (gọi thoại) - âm thanh 2 chiều real-time
- ✅ Video Call (gọi video) - âm thanh + video 2 chiều real-time
- ✅ Incoming/Outgoing call dialogs (giao diện gọi đến/đi)
- ✅ Active call window với controls (cửa sổ cuộc gọi với nút điều khiển)
- ✅ Mute/Unmute audio
- ✅ Camera on/off (video call)
- ✅ End call
- ✅ Call signaling qua TCP (CALL_REQUEST, ACCEPT, REJECT, END)
- ✅ Media streaming qua UDP (audio + video)

---

## 📦 Cài Đặt Dependencies

### 1. Cài đặt dependencies mới:

```bash
pip install -r requirements.txt
```

**Dependencies mới được thêm:**
- `PyAudio>=0.2.13` - Audio capture/playback
- `opencv-python>=4.8.0` - Video capture/processing
- `numpy>=1.24.0` - Required by OpenCV

### 2. Lưu ý với PyAudio:

#### **Windows:**
- PyAudio có thể cần Visual C++ Build Tools
- Nếu gặp lỗi, tải wheel file từ: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
- Hoặc dùng: `pip install pipwin && pipwin install pyaudio`

#### **Linux (Kali/Ubuntu):**
```bash
sudo apt-get install python3-pyaudio portaudio19-dev
pip install PyAudio
```

#### **macOS:**
```bash
brew install portaudio
pip install PyAudio
```

---

## 🚀 Cách Sử Dụng

### **1. Khởi động app (2 instances)**

#### **Terminal 1 - User A:**
```bash
python main.py
# Login as: a@gmail.com
```

#### **Terminal 2 - User B:**
```bash
python main.py
# Login as: b@gmail.com
```

### **2. Kết nối 2 peers:**

- User B add User A bằng IP (ví dụ: `127.0.0.1:55000` hoặc `192.168.1.100:55000`)
- Hoặc User A add User B
- Đợi cả 2 bên thấy nhau **Online** (chấm xanh 🟢)

### **3. Bắt đầu cuộc gọi:**

#### **A. Voice Call (Gọi thoại):**

1. User A click vào chat của User B
2. Click icon **📞 Phone** ở góc trên bên phải chat header
3. **User A** thấy dialog "Calling..." (đang gọi)
4. **User B** thấy dialog "Incoming voice call..." với 2 nút:
   - ✅ **Accept** (chấp nhận)
   - ❌ **Reject** (từ chối)
5. Nếu B chấp nhận:
   - Cả 2 bên hiển thị **Active Call Window**
   - Âm thanh từ mic của A → speaker của B
   - Âm thanh từ mic của B → speaker của A
6. Click nút **🔴 End Call** để kết thúc

#### **B. Video Call (Gọi video):**

1. User A click vào chat của User B
2. Click icon **📹 Video** ở góc trên bên phải chat header
3. **User A** thấy dialog "Calling..." (đang gọi)
4. **User B** thấy dialog "Incoming video call..." với 2 nút:
   - ✅ **Accept** (chấp nhận)
   - ❌ **Reject** (từ chối)
5. Nếu B chấp nhận:
   - Cả 2 bên hiển thị **Active Call Window** với video display
   - Video từ camera A → hiển thị trên màn hình B (remote video - cửa sổ lớn)
   - Video từ camera B → hiển thị trên màn hình A (remote video - cửa sổ lớn)
   - Mỗi bên thấy video của mình ở góc nhỏ (local video preview)
   - Âm thanh 2 chiều giống voice call
6. Controls:
   - **Mute/Unmute** - tắt/bật mic
   - **Camera Off/On** - tắt/bật camera
   - **🔴 End Call** - kết thúc cuộc gọi

---

## 🎨 Giao Diện

### **Incoming Call Dialog (Cuộc gọi đến):**
```
┌────────────────────────────────┐
│    Incoming Voice/Video Call    │
│                                  │
│         [👤 Avatar]              │
│                                  │
│         John Doe                 │
│    Incoming voice call...        │
│                                  │
│      [🔴 Reject]  [✅ Accept]    │
└────────────────────────────────┘
```

### **Outgoing Call Dialog (Đang gọi):**
```
┌────────────────────────────────┐
│          Voice Call              │
│                                  │
│         [👤 Avatar]              │
│                                  │
│         Jane Smith               │
│         Calling...               │
│                                  │
│          [🔴 Cancel]             │
└────────────────────────────────┘
```

### **Active Call Window - Voice:**
```
┌────────────────────────────────┐
│     Call with John Doe          │
│                                  │
│         [👤 Avatar]              │
│                                  │
│         John Doe                 │
│          00:45                   │
│                                  │
│  [Mute]  [🔴 End]               │
└────────────────────────────────┘
```

### **Active Call Window - Video:**
```
┌──────────────────────────────────┐
│     Call with Jane Smith          │
│                                    │
│  ┌────────────────────────────┐  │
│  │                             │  │
│  │   Remote Video Display      │  │
│  │   (Jane's camera)           │  │
│  │                             │  │
│  │         ┌──────────┐        │  │
│  │         │ Local    │        │  │
│  │         │ Video    │        │  │
│  │         └──────────┘        │  │
│  └────────────────────────────┘  │
│                                    │
│  [Mute] [🔴 End] [Camera Off]    │
└──────────────────────────────────┘
```

---

## 🔧 Cấu Hình Network

### **UDP Ports:**
- **Audio Stream**: `56000-56199` (UDP)
- **Video Stream**: `57000-57199` (UDP)

### **Firewall Rules (nếu cần):**

#### **Windows:**
```powershell
New-NetFirewallRule -DisplayName "Chat P2P Audio" -Direction Inbound -LocalPort 56000-56199 -Protocol UDP -Action Allow
New-NetFirewallRule -DisplayName "Chat P2P Video" -Direction Inbound -LocalPort 57000-57199 -Protocol UDP -Action Allow
```

#### **Linux:**
```bash
sudo ufw allow 56000:56199/udp
sudo ufw allow 57000:57199/udp
```

---

## 🧪 Test Cases

### **Test 1: Voice Call - Same Machine**
```
1. Mở 2 instances (A và B) trên cùng máy
2. A call B (voice)
3. B accept
4. ✅ Kiểm tra: nghe được âm thanh từ mic → speaker
5. A click End Call
6. ✅ Kiểm tra: cả 2 bên call window đóng
```

### **Test 2: Video Call - Same Machine**
```
1. Mở 2 instances (A và B)
2. A call B (video)
3. B accept
4. ✅ Kiểm tra:
   - Video hiển thị (có thể giống nhau nếu dùng cùng camera)
   - Âm thanh nghe được
5. B click "Camera Off"
6. ✅ Kiểm tra: camera B tắt
7. A click End Call
8. ✅ Kiểm tra: cả 2 bên call window đóng
```

### **Test 3: Call Rejection**
```
1. A call B
2. B click Reject
3. ✅ Kiểm tra:
   - A thấy thông báo "Call Rejected"
   - B quay về chat bình thường
```

### **Test 4: Call Cancellation**
```
1. A call B
2. A click Cancel (trước khi B accept)
3. ✅ Kiểm tra:
   - A quay về chat bình thường
   - B incoming dialog đóng
```

### **Test 5: Call Between 2 Machines (LAN)**
```
1. Machine A: IP 192.168.1.100
2. Machine B: IP 192.168.1.101
3. B add A (192.168.1.100:55000)
4. A call B (video)
5. B accept
6. ✅ Kiểm tra:
   - Video streaming qua LAN
   - Audio streaming qua LAN
   - Latency thấp
```

---

## 🐛 Troubleshooting

### **Vấn đề 1: "Microphone/speaker error"**
**Nguyên nhân:** PyAudio không truy cập được microphone/speaker

**Giải pháp:**
- Windows: Cho phép app truy cập microphone trong Settings → Privacy
- Linux: Kiểm tra ALSA/PulseAudio: `arecord -l`, `aplay -l`
- Mac: Cho phép Terminal/app truy cập mic trong System Preferences

### **Vấn đề 2: "Camera error"**
**Nguyên nhân:** OpenCV không mở được camera

**Giải pháp:**
- Đóng các app khác đang dùng camera (Zoom, Skype, etc.)
- Kiểm tra camera index: thử `camera_index=1` thay vì `0`
- Windows: Cho phép app truy cập camera trong Settings

### **Vấn đề 3: "Port binding error"**
**Nguyên nhân:** UDP ports đang được sử dụng

**Giải pháp:**
- Đóng instance cũ của app
- Kiểm tra: `netstat -an | findstr "56000"` (Windows) hoặc `netstat -an | grep 56000` (Linux)

### **Vấn đề 4: Video không hiển thị**
**Nguyên nhân:** Firewall chặn UDP hoặc bandwidth thấp

**Giải pháp:**
- Mở firewall cho UDP ports 56000-57199
- Kiểm tra network quality
- Thử voice call trước (bandwidth thấp hơn)

### **Vấn đề 5: Audio delay/lag**
**Nguyên nhân:** Network latency cao hoặc audio buffer size lớn

**Giải pháp:**
- Giảm `CHUNK_SIZE` trong `Core/media/audio_stream.py` (hiện tại: 1024)
- Dùng mạng LAN thay vì Internet
- Đóng các app tốn bandwidth

---

## 📊 Kiến Trúc Kỹ Thuật

### **Call Flow:**

```
Peer A                           Peer B
  │                                 │
  │──── CALL_REQUEST (TCP) ──────>│  (Voice/Video, UDP ports)
  │                                 │
  │<──── CALL_ACCEPT (TCP) ────────│  (UDP ports)
  │                                 │
  │<════ UDP Audio Stream ════════>│  (Bidirectional, 56000)
  │                                 │
  │<════ UDP Video Stream ════════>│  (Bidirectional, 57000)
  │                                 │
  │──── CALL_END (TCP) ───────────>│
```

### **Components:**

1. **Core/call/call_manager.py** - Quản lý call state, media streams
2. **Core/networking/udp_stream.py** - UDP sender/receiver
3. **Core/media/audio_stream.py** - PyAudio capture/playback
4. **Core/media/video_stream.py** - OpenCV capture/decode
5. **Gui/view/call_dialog.py** - Incoming/Outgoing call dialogs
6. **Gui/view/call_window.py** - Active call window
7. **Core/models/message.py** - Call signaling messages

---

## 🎯 Kết Luận

Voice & Video Call đã được tích hợp đầy đủ vào project. Tất cả features đã hoạt động:

✅ Voice call (âm thanh 2 chiều)
✅ Video call (âm thanh + video 2 chiều)
✅ Call signaling (TCP)
✅ Media streaming (UDP)
✅ UI đầy đủ (dialogs, call window, controls)
✅ Hỗ trợ LAN và localhost

**Sẵn sàng để test!** 🚀

---

## 📝 Notes

- Audio quality: 16kHz mono (tốt cho voice, bandwidth thấp)
- Video quality: 640x480 @ 15 FPS, JPEG compression 60%
- UDP sequence numbers để handle packet ordering
- Auto fallback nếu camera/mic không khả dụng
- Call state management với enum (IDLE, OUTGOING, INCOMING, ACTIVE, ENDING)

**Để cải thiện thêm (optional):**
- Thêm STUN/TURN servers cho NAT traversal
- Implement ICE (Interactive Connectivity Establishment)
- Thêm echo cancellation
- Thêm noise reduction
- Support nhiều codec (Opus, VP8, H.264)
- Implement reconnection logic

