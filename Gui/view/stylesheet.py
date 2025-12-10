# stylesheet.py
STYLESHEET = """
/* --- Màu nền chung --- */
QMainWindow, QWidget {
    background-color: #F8F9FA; /* Màu nền chính */
    color: #333333;
    font-family: 'Segoe UI', 'Arial', sans-serif;
}

/* --- Bộ chia cột (Splitter) --- */
QSplitter::handle {
    background-color: transparent; /* Ẩn bộ chia */
    width: 1px;
}

/* --- Khung chung cho 3 cột --- */
QFrame#LeftSidebar, QFrame#CenterPanel {
    background-color: #FFFFFF; /* Màu nền trắng cho các panel */
    border-radius: 10px;
}
QFrame#RightSidebar {
    background-color: transparent;
    border: none;
    padding: 0px; /* Xóa mọi padding cũ */
}
/* Cột giữa không cần bo góc để liền mạch */
QFrame#CenterPanel {
    border-radius: 0px;
    border-left: 1px solid #F0F0F0;
    border-right: 1px solid #F0F0F0;
}

/* =========================================== */
/* === CỘT BÊN TRÁI (ChatList) === */
/* =========================================== */
QFrame#LeftSidebar {
    padding: 10px;
}

QFrame#LeftSidebar {
    padding: 10px;
}

QFrame#HeaderDivider {
    background-color: #E0E0E0;
}

#UserNameLabel {
    color: #222;
    font-weight: bold;
    font-size: 24px;
    background-color: transparent
}

#HeaderUserAvatar {
    background-color: transparent;
}

/* Icon Nav (cần dùng QIcon/ảnh thật) */
QLabel.NavIcon {
    font-size: 20px;
    padding: 5px;
    color: #AAAAAA; /* [THAY ĐỔI] Cho màu xám nhạt */
    border-radius: 5px;
}

QLabel.NavIcon:hover {
    color: #555555; /* [THÊM MỚI] Đổi màu khi hover */
    background-color: #F0F0F0;
}

QLabel#NavIconActive {
    font-size: 20px;
    padding: 5px;
    color: #6B47D9; /* Màu tím */
}

/* Tiêu đề "Chats" */
QLabel#ChatsHeader {
    font-size: 28px;
    font-weight: bold;
    padding: 10px 5px;
    background-color: transparent;
}

/* Nút dấu cộng (+) */
QPushButton#PlusButton {
    background-color: #6B47D9; /* Màu tím */
    font-weight: bold;
    font-size: 20px;
    border: none;
    border-radius: 13px; /* (26px / 2) */
    min-width: 26px;
    max-width: 26px;
    min-height: 26px;
    max-height: 26px;
}

/* Các tab (DIRECT, GROUPS, PUBLIC) */
QLabel.TabLabel {
    font-size: 11px;
    font-weight: bold;
    color: #AAAAAA; /* Màu xám cho tab không active */
    padding: 5px;
    background-color: transparent;
}

QLabel.TabLabel:hover {
    color: #555555; /* Màu đậm hơn khi hover */
}

QLabel#TabLabelActive {
    font-size: 11px;
    font-weight: bold;
    color: #555555; /* Màu tím cho tab active */
    border-bottom: 2px solid #555555;
    padding: 5px;
    background-color: transparent;
}

/* Thanh tìm kiếm */
QLineEdit#SearchBar {
    background-color: #F1F3F5; /* Màu xám nhạt */
    border: none;
    border-radius: 10px;
    padding: 10px 15px;
    font-size: 13px;
}

/* Danh sách chat */
QListWidget#ChatList {
    border: none;
    outline: none;
    background-color: transparent;
}
QListWidget::item:focus, QListWidget::item:selected {
    border: none;
    outline: none;
    background-color: transparent;
}

/* =========================================== */
/* === MỤC CHAT (ChatItemWidget) === */
/* =========================================== */

QFrame#ChatItemWidget {
    background-color: #F1F3F5; /* Màu xám nhạt */
    padding: 8px;
    border-radius: 8px;
}
/* Style cho item khi được CHỌN */
QFrame#ChatItemWidgetActive {
    background-color: #3D434A; /* Màu nền tối khi active */
    padding: 8px;
    border-radius: 8px;
    background-color: parent;
}

QFrame#ChatItemWidget:hover {
    background-color: #B8B8B8; /* Màu xám siêu nhạt */
}

/* Avatar (ảnh đại diện) */
QLabel#AvatarLabel {
    border-radius: 20px; /* (40px / 2) */
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
}

/* Avatar container với online indicator */
QFrame#AvatarContainer {
    background-color: transparent;
    min-width: 40px;
    max-width: 40px;
}

/* Online indicator (dấu chấm đỏ) */
QLabel#OnlineIndicator {
    background-color: #4CAF50; /* Màu xanh lá (online) */
    border-radius: 6px; /* Tròn */
    border: 2px solid #FFFFFF; /* Viền trắng */
    min-width: 12px;
    max-width: 12px;
    min-height: 12px;
    max-height: 12px;
}

/* Tên người dùng */
QLabel#NameLabel {
    font-size: 14px;
    font-weight: bold;
    color: #333;
    background-color: transparent;
}
QFrame#ChatItemWidgetActive QLabel#NameLabel {
    color: #FFFFFF !important;
}

/* Tin nhắn cuối */
QLabel#MessageLabel {
    font-size: 13px;
    color: #777;
    background-color: transparent;
}
QFrame#ChatItemWidgetActive QLabel#MessageLabel {
    color: #DDD !important;
}

/* Thời gian */
QLabel#TimeLabel {
    font-size: 11px;
    color: #999;
    background-color: transparent;
}
QFrame#ChatItemWidgetActive QLabel#TimeLabel {
    color: #BBB !important;
    background-color: transparent;
}

/* Số tin nhắn chưa đọc */
QLabel#UnreadCountLabel {
    background-color: #6B47D9; /* Màu tím */
    color: white;
    font-size: 11px;
    font-weight: bold;
    border-radius: 8px; /* (16px / 2) */
    min-width: 16px;
    max-width: 25px;
    min-height: 16px;
    max-height: 16px;
    padding: 0 4px;
}
/* =========================================== */
/* === CỘT Ở GIỮA (ChatArea) === */
/* =========================================== */
/* Header của khung chat (Kirti Yadav) */
QFrame#ChatHeader {
    background-color: #FFFFFF;
    border-bottom: 1px solid #F0F0F0;
    padding: 10px 20px;
}
QFrame#ChatHeader QLabel#NameLabel {
    font-size: 16px; /* Tên to hơn */
}
QFrame#ChatHeader QLabel#MessageLabel {
    font-size: 12px; /* Status nhỏ hơn */
}

QPushButton#IconButton {
    border: none; 
    padding: 5px;
    background-color: transparent;
}

QPushButton#IconButton:hover {
    background-color: #F0F0F0;
    border-radius: 4px;
}

QLabel#ChatAvatarLabel {
    background-color: transparent;
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
}

/* Khu vực cuộn tin nhắn */
QScrollArea#MessageArea {
    border: none;
    background-color: #F8F9FA; /* Nền xám nhạt cho khu vực chat */
}
QWidget#MessageContent {
    background-color: transparent;
    padding: 15px;
}

/* Dấu phân cách ngày tháng */
QLabel#DateSeparator {
    color: #999;
    font-size: 12px;
    font-weight: bold;
    padding: 10px;
    qproperty-alignment: 'AlignCenter';
}

/* =========================================== */
/* === BONG BÓNG CHAT (MessageBubble) === */
/* =========================================== */
QLabel.MessageBubble {
    font-size: 14px;
    padding: 10px 14px;
    max-width: 450px; /* Giới hạn chiều rộng */
    qproperty-wordWrap: true; 
}
/* Tin nhắn của mình (bên phải): Bo 4px ở góc dưới phải */
QLabel#MessageBubbleSelf {
    background-color: #6B47D9;
    color: white;
    border-radius: 18px 18px 4px 18px;
}
/* Tin nhắn của người khác (bên trái): Bo 4px ở góc dưới trái */
QLabel#MessageBubbleOther {
    background-color: #F1F3F5;
    color: #333;
    border-radius: 18px 18px 18px 4px;
}

/* Khung nhập tin nhắn */
QFrame#ChatInputBar {
    background-color: #FFFFFF;
    border-top: 1px solid #F0F0F0;
    padding: 10px 20px;
}
QLineEdit#MessageInput {
    background-color: #F8F9FA; /* Nền xám nhạt */
    border: none;
    border-radius: 18px;
    padding: 12px 18px;
    font-size: 14px;
    color: #333;
}
/* Nút Gửi (Placeholder) */
QPushButton#SendButton {
    background-color: #6B47D9;
    color: white;
    border: none;
    border-radius: 18px; /* (36px / 2) */
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    font-weight: bold;
    font-size: 16px;
}


/* =========================================== */
/* === CỘT BÊN PHẢI (NotificationsPanel) === */
/* =========================================== */
QFrame#RightSidebar {
    padding: 15px 20px;
    background-color: transparent;
}

QWidget#SidebarScrollContent {
    background-color: transparent;
}

QScrollArea#SidebarScrollArea {
    border: none;
    background-color: transparent;
}

QFrame#RightSidebar > QFrame {
    background-color: transparent;
}

/* Tiêu đề "Notifications", "Suggestions" */
QLabel#SidebarHeader {
    font-size: 18px;
    font-weight: bold;
    color: #333;
    margin-top: 15px;
    margin-bottom: 10px;
    background-color: transparent;
}

/* Chữ "Create memorable talks" */
QLabel#CreateTalksLabel {
    font-size: 13px;
    font-weight: bold;
    color: #6B47D9;
    padding-bottom: 10px;
    qproperty-alignment: 'AlignRight';
}
QLabel#CreateTalksLabel:hover {
    color: #5538A8;
}

/* Avatar trong thông báo */
QLabel#NotificationAvatar {
    background-color: #E0E0E0;
    border-radius: 17px; /* (35px / 2) */
    min-width: 35px;
    max-width: 35px;
    min-height: 35px;
    max-height: 35px;
}

/* Nút Add */
QPushButton#AddButton {
    background-color: #E8E4F8; /* Nền tím nhạt */
    color: #6B47D9; /* Chữ tím */
    font-weight: bold;
    font-size: 12px;
    border: none;
    border-radius: 12px;
    padding: 5px 15px;
    min-height: 24px;
}
QPushButton#AddButton:hover {
    background-color: #DCD6F4;
}

/* =========================================== */
/* === STYLE THANH CUỘN (SCROLLBAR) === */
/* =========================================== */

/* Áp dụng cho cả thanh cuộn dọc và ngang */
QScrollBar:vertical, QScrollBar:horizontal {
    border: none;
    background-color: #F0F0F0; /* Màu của rãnh cuộn (track) */
    width: 8px;                /* Chiều rộng cho thanh cuộn dọc */
    height: 8px;               /* Chiều cao cho thanh cuộn ngang */
    margin: 0px;
}

/* Phần tay cầm (handle) của thanh cuộn */
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background-color: #C1C1C1; /* Màu của tay cầm */
    border-radius: 4px;        /* Bo tròn tay cầm */
    min-height: 20px;          /* Chiều cao tối thiểu (cho thanh dọc) */
    min-width: 20px;           /* Chiều rộng tối thiểu (cho thanh ngang) */
}

/* Hiệu ứng khi di chuột qua tay cầm */
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background-color: #A1A1A1; /* Màu đậm hơn khi hover */
}

/* Ẩn các nút mũi tên (add-line, sub-line) */
QScrollBar::add-line, QScrollBar::sub-line {
    border: none;
    background: none;
    height: 0px;
    width: 0px;
}

/* Ẩn phần rãnh cuộn (add-page, sub-page) */
/* (Phần rãnh đã được style ở QScrollBar:vertical) */
QScrollBar::add-page, QScrollBar::sub-page {
    background: none;
}

/* =========================================== */
/* === PREVIEW AREA (File Attachments) === */
/* =========================================== */
QWidget#PreviewArea {
    background-color: #f9f9f9;
    border-top: 1px solid #e0e0e0;
}

QWidget#PreviewItem {
    background-color: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 8px;
}

QPushButton#PreviewRemoveButton {
    background-color: #ff4444;
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 14px;
    font-weight: bold;
}

QPushButton#PreviewRemoveButton:hover {
    background-color: #cc0000;
}

/* =========================================== */
/* === MESSAGE BUBBLE FILE WIDGETS === */
/* =========================================== */
QLabel#MessageImageLabel {
    background-color: transparent;
    border: none;
    border-radius: 12px;
    padding: 0px;
}

QWidget#FileContainer {
    background-color: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 0px;
}

QLabel#FileNameLabel {
    font-size: 13px;
    font-weight: 500;
    color: #333;
}

QLabel#FileTypeLabel {
    font-size: 11px;
    color: #999;
}

QLabel#FileIconLabel {
    font-size: 24px;
}

QPushButton#FileDownloadButton {
    background-color: #007AFF;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton#FileDownloadButton:hover {
    background-color: #0051D5;
}

QPushButton#FileDownloadButton:pressed {
    background-color: #0040B3;
}

QLabel#FileErrorLabel {
    font-size: 12px;
    color: #666;
    padding: 5px;
}

/* =========================================== */
/* === CALL WINDOW STYLES === */
/* =========================================== */
QFrame#VideoContainer {
    background-color: #1a1a1a;
}

QLabel#RemoteVideoLabel {
    background-color: #2a2a2a;
    color: #999;
    font-size: 16px;
}

QLabel#LocalVideoLabel {
    background-color: #3a3a3a;
    border: 2px solid #555;
    border-radius: 8px;
}

QLabel#CallAvatarLabel {
    font-size: 24px;
    font-weight: bold;
    color: #333;
}

QLabel#CallStatusLabel {
    font-size: 18px;
    color: #666;
}

QFrame#ControlsPanel {
    background-color: #f5f5f5;
    border-top: 1px solid #ddd;
}

QPushButton#MuteButton {
    background-color: #4CAF50;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
}

QPushButton#MuteButton:hover {
    background-color: #45a049;
}

QPushButton#MuteButton:checked {
    background-color: #ff9800;
}

QPushButton#MuteButton:checked:hover {
    background-color: #e68900;
}

QPushButton#EndCallButton {
    background-color: #ff4444;
    border: none;
    border-radius: 30px;
}

QPushButton#EndCallButton:hover {
    background-color: #cc0000;
}

QPushButton#CameraButton {
    background-color: #2196F3;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
}

QPushButton#CameraButton:hover {
    background-color: #0b7dda;
}

/* =========================================== */
/* === CALL DIALOG STYLES === */
/* =========================================== */
QLabel#DialogCallerName {
    font-size: 22px;
    font-weight: bold;
    color: #333;
}

QLabel#DialogCallType {
    font-size: 16px;
    color: #666;
}

QLabel#DialogStatus {
    font-size: 16px;
    color: #666;
}

QPushButton#RejectCallButton {
    background-color: #ff4444;
    border: none;
    border-radius: 30px;
}

QPushButton#RejectCallButton:hover {
    background-color: #cc0000;
}

QPushButton#AcceptCallButton {
    background-color: #4CAF50;
    border: none;
    border-radius: 30px;
}

QPushButton#AcceptCallButton:hover {
    background-color: #45a049;
}

QPushButton#CancelCallButton {
    background-color: #ff4444;
    border: none;
    border-radius: 30px;
}

QPushButton#CancelCallButton:hover {
    background-color: #cc0000;
}

/* =========================================== */
/* === ADD FRIEND STYLES === */
/* =========================================== */
QLineEdit#AddFriendInput {
    background-color: #F1F3F5;
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit#AddFriendInput:focus {
    border: 1px solid #4A90E2;
}

QPushButton#AddFriendButton {
    background-color: #4A90E2;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    padding: 8px 16px;
}

QPushButton#AddFriendButton:hover {
    background-color: #3A7BC8;
}

QPushButton#AddFriendButton:pressed {
    background-color: #2A6BB0;
}

/* =========================================== */
/* === EMOJI PICKER DIALOG === */
/* =========================================== */
QPushButton#EmojiButton {
    border: none;
    background: transparent;
    font-size: 24px;
}

QPushButton#EmojiButton:hover {
    background-color: rgba(0,0,0,0.1);
}

QPushButton#EmojiCloseButton {
    background-color: #4A90E2;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    padding: 8px 16px;
}

QPushButton#EmojiCloseButton:hover {
    background-color: #3A7BC8;
}

/* =========================================== */
/* === NETWORK INFO LABELS === */
/* =========================================== */
QLabel#NetworkInfoLabel {
    font-size: 12px;
    color: #2196F3;
    font-weight: bold;
}

QLabel#NetworkInfoLabelInactive {
    font-size: 11px;
    color: #999;
}

/* =========================================== */
/* === NOTIFICATION PANEL LABELS === */
/* =========================================== */
QLabel#NotificationTextLabel {
    font-size: 13px;
    color: #555;
}

QLabel#NotificationTimeLabel {
    color: #AAA;
    font-size: 11px;
}

QLabel#FormLabel {
    font-size: 12px;
    color: #555;
}

/* =========================================== */
/* === MESSAGE TIMESTAMP === */
/* =========================================== */
QLabel#MessageTimestamp {
    font-size: 10px;
    color: #999;
    padding: 2px 5px;
}

QLabel#FileTextLabel {
    background-color: transparent;
    padding: 0px;
}

"""