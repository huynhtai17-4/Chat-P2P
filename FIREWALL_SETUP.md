# Firewall Setup Guide

## Vấn đề: Không nhận được tin nhắn / Peer hiển thị offline

App Chat P2P cần mở **cổng TCP 55000-55199** để có thể nhận tin nhắn và status từ peers khác.

---

## 🐧 Linux (Kali, Ubuntu, etc.)

### Cách 1: Dùng script tự động (Khuyên dùng)

```bash
# Mở firewall
sudo bash setup_firewall.sh

# Kiểm tra network
bash check_network.sh
```

### Cách 2: Thủ công

#### UFW (Ubuntu, Debian, Kali)
```bash
sudo ufw allow 55000:55199/tcp
sudo ufw allow 55000:55199/udp
sudo ufw reload
```

#### firewalld (Fedora, CentOS, RHEL)
```bash
sudo firewall-cmd --permanent --add-port=55000-55199/tcp
sudo firewall-cmd --permanent --add-port=55000-55199/udp
sudo firewall-cmd --reload
```

#### iptables
```bash
sudo iptables -I INPUT -p tcp --dport 55000:55199 -j ACCEPT
sudo iptables -I INPUT -p udp --dport 55000:55199 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

---

## 🪟 Windows

### Cách 1: Dùng script tự động (Khuyên dùng)

1. Chuột phải vào `setup_firewall.bat`
2. Chọn **"Run as administrator"**

### Cách 2: Thủ công qua PowerShell (Admin)

```powershell
# TCP
New-NetFirewallRule -DisplayName "Chat P2P - TCP" -Direction Inbound -Protocol TCP -LocalPort 55000-55199 -Action Allow

# UDP (for calls)
New-NetFirewallRule -DisplayName "Chat P2P - UDP" -Direction Inbound -Protocol UDP -LocalPort 55000-55199 -Action Allow
```

### Cách 3: Qua GUI

1. Mở **Windows Defender Firewall** → **Advanced Settings**
2. Click **Inbound Rules** → **New Rule**
3. Chọn **Port** → Next
4. Chọn **TCP** và nhập `55000-55199` → Next
5. Chọn **Allow the connection** → Next
6. Chọn **Private, Domain** → Next
7. Đặt tên: `Chat P2P - TCP` → Finish
8. Lặp lại cho **UDP**

---

## Kiểm tra kết nối

### Trên máy nhận (bị lỗi không nhận tin nhắn)

1. Chạy app
2. Kiểm tra port đang listen:
   - Linux: `ss -tuln | grep 55000`
   - Windows: `netstat -an | findstr 55000`
3. Nếu thấy `0.0.0.0:55000` → App đã mở port ✅
4. Nếu không thấy → App chưa chạy hoặc lỗi ❌

### Từ máy gửi

Thử ping và telnet:
```bash
# Ping IP của máy nhận
ping 192.168.1.x

# Test kết nối TCP (cần telnet/nc)
telnet 192.168.1.x 55000
# Hoặc
nc -zv 192.168.1.x 55000
```

Nếu telnet kết nối được → Firewall đã mở ✅  
Nếu bị refuse/timeout → Firewall vẫn block ❌

---

## Các dấu hiệu Firewall đang block

1. ✅ Máy A gửi tin → Máy B nhận được
2. ❌ Máy B gửi tin → Máy A **KHÔNG** nhận được
3. ❌ Máy A hiển thị Máy B là **"Offline"** (không nhận status)
4. ❌ Avatar không hiển thị đúng (không nhận avatar data)

→ **Máy A đang bị firewall block incoming connections!**

---

## Troubleshooting

### Vẫn không nhận được tin nhắn sau khi mở firewall?

1. **Restart app** sau khi mở firewall
2. Kiểm tra **router/modem**: Một số router có firewall riêng
3. Kiểm tra **antivirus**: Kaspersky, McAfee, Avast có thể block
4. Kiểm tra IP đúng: Dùng IP hiển thị ở panel bên phải app
5. Đảm bảo cả 2 máy cùng subnet (VD: `192.168.1.x`)

### Debug mode

Xem log chi tiết khi chạy app:
```bash
# Linux
python3 main.py 2>&1 | tee chat_debug.log

# Windows
python main.py > chat_debug.log 2>&1
```

Tìm dòng:
- `[TCP] Listener started on port 55000` → OK ✅
- `Failed to start PeerListener` → Lỗi ❌
- `Error in on_message callback` → Firewall block ❌

---

## Port Usage

| Port Range     | Protocol | Usage                |
|----------------|----------|----------------------|
| 55000-55199    | TCP      | Messages, status, files |
| 55000-55199    | UDP      | Audio/Video calls    |

**Lưu ý**: Chỉ cần mở port mà app đang dùng (thường là 55000). Nếu port 55000 bị chiếm, app sẽ tự động dùng port khác trong range 55000-55199.

