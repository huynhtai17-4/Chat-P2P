# chat_list_controller.py
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QListWidgetItem
from Gui.view.chat_item import ChatItemWidget


class ChatListController(QObject):
    # Signals
    chat_selected = Signal(str, str)  # chat_id, chat_name
    tab_changed = Signal(str)  # tab_name
    search_performed = Signal(str)  # search_text
    
    def __init__(self, chat_list_widget):
        super().__init__()
        self.chat_list_widget = chat_list_widget
        self.search_input = None
        self.tab_labels = {}
        self.current_tab = "DIRECT"
        self.current_chat_item = None
        self.all_chat_items = []
        self._peer_refresh_handler = None
        
        # Kết nối signals
        self._connect_signals()
    
    def _connect_signals(self):
        """Kết nối tất cả signals từ UI"""
        # Kết nối click trên list widget
        self.chat_list_widget.itemClicked.connect(self._on_chat_item_clicked)
        
        # Kết nối double click để có thể thêm hành động khác
        self.chat_list_widget.itemDoubleClicked.connect(self._on_chat_item_double_clicked)
    
    def set_search_input(self, search_input):
        """Thiết lập search input và kết nối signal"""
        self.search_input = search_input
        if self.search_input:
            self.search_input.textChanged.connect(self._on_search_text_changed)
    
    def set_tab_labels(self, direct_tab, groups_tab, public_tab):
        """Thiết lập các tab labels và kết nối events"""
        self.tab_labels = {
            "DIRECT": direct_tab,
            "GROUPS": groups_tab,
            "PUBLIC": public_tab
        }
        
        # Thiết lập mouse events cho các tab
        for tab_name, tab_label in self.tab_labels.items():
            tab_label.mousePressEvent = self._create_tab_click_handler(tab_name)
    
    def _create_tab_click_handler(self, tab_name):
        """Tạo handler cho click trên tab"""
        def handler(event):
            if event.button() == Qt.LeftButton:
                self.switch_tab(tab_name)
        return handler
    
    def switch_tab(self, tab_name):
        """Chuyển đổi tab và cập nhật giao diện"""
        if tab_name not in self.tab_labels or tab_name == self.current_tab:
            return
        
        # Cập nhật trạng thái tab cũ
        old_tab = self.tab_labels[self.current_tab]
        old_tab.setObjectName("TabLabel")
        old_tab.style().unpolish(old_tab)
        old_tab.style().polish(old_tab)
        
        # Cập nhật trạng thái tab mới
        new_tab = self.tab_labels[tab_name]
        new_tab.setObjectName("TabLabelActive")
        new_tab.style().unpolish(new_tab)
        new_tab.style().polish(new_tab)
        
        self.current_tab = tab_name

        self._filter_chats_by_tab(tab_name)

        self.tab_changed.emit(tab_name)
        self.request_peer_refresh()

    def _filter_chats_by_tab(self, tab_name):
        """Filter chat items theo tab selected"""
        # TODO: Implement logic filter theo tab nếu cần
        # Hiện tại hiển thị tất cả, có thể customize theo需求
        pass

    def _on_search_text_changed(self, text):
        """Xử lý khi text search thay đổi"""
        search_text = text.strip().lower()
        self._filter_chats(search_text)
        self.search_performed.emit(search_text)
    
    def _filter_chats(self, search_text):
        """Filter chat items dựa trên search text"""
        if not self.all_chat_items:
            # Lưu tất cả items ban đầu nếu chưa có
            self._cache_all_chat_items()
        
        if not search_text:
            # Hiển thị tất cả nếu search rỗng
            self._show_all_chats()
            return
        
        # Ẩn tất cả items trước
        for i in range(self.chat_list_widget.count()):
            self.chat_list_widget.item(i).setHidden(True)
        
        # Hiển thị items phù hợp
        for list_item, chat_data in self.all_chat_items:
            chat_widget = self.chat_list_widget.itemWidget(list_item)
            if chat_widget and self._chat_matches_search(chat_widget, search_text):
                list_item.setHidden(False)
    
    def _cache_all_chat_items(self):
        """Cache tất cả chat items ban đầu"""
        self.all_chat_items = []
        for i in range(self.chat_list_widget.count()):
            list_item = self.chat_list_widget.item(i)
            chat_widget = self.chat_list_widget.itemWidget(list_item)
            if chat_widget:
                self.all_chat_items.append((list_item, {
                    'name': getattr(chat_widget, 'contact_name', ''),
                    'last_message': getattr(chat_widget, 'last_message', ''),
                    'time': getattr(chat_widget, 'time_label', '')
                }))
    
    def _chat_matches_search(self, chat_widget, search_text):
        """Kiểm tra chat item có khớp với search text không"""
        # Tìm trong tên
        contact_name = getattr(chat_widget, 'contact_name', '').lower()
        if search_text in contact_name:
            return True
        
        # Tìm trong tin nhắn cuối
        last_message = getattr(chat_widget, 'last_message', '').lower()
        if search_text in last_message:
            return True
        
        return False
    
    def _show_all_chats(self):
        """Hiển thị tất cả chat items"""
        for list_item, _ in self.all_chat_items:
            list_item.setHidden(False)
    
    def _on_chat_item_clicked(self, item):
        """Xử lý khi click vào chat item"""
        if not item:
            return
            
        chat_widget = self.chat_list_widget.itemWidget(item)
        if not chat_widget:
            return
        
        # Bỏ chọn item cũ (nếu có) - kiểm tra item còn hợp lệ
        if self.current_chat_item:
            try:
                # Kiểm tra item còn tồn tại trong list
                row = self.chat_list_widget.row(self.current_chat_item)
                if row >= 0:
                    old_widget = self.chat_list_widget.itemWidget(self.current_chat_item)
                    if old_widget and hasattr(old_widget, 'set_selected'):
                        old_widget.set_selected(False)
            except (RuntimeError, AttributeError):
                # Item đã bị xóa, bỏ qua
                self.current_chat_item = None
        
        # Chọn item mới
        if hasattr(chat_widget, 'set_selected'):
            chat_widget.set_selected(True)
        
        self.current_chat_item = item
        
        # Lấy thông tin chat
        chat_id = self._get_chat_id(chat_widget)
        chat_name = getattr(chat_widget, 'contact_name', '')
        
        # Phát signal
        self.chat_selected.emit(chat_id, chat_name)
    
    def _on_chat_item_double_clicked(self, item):
        """Xử lý khi double click vào chat item"""
        chat_widget = self.chat_list_widget.itemWidget(item)
        if chat_widget:
            # Có thể thêm hành động khác cho double click
            pass
    
    def _get_chat_id(self, chat_widget):
        """Lấy chat ID từ widget (peer_id nếu có, nếu không thì dùng tên)"""
        # Ưu tiên dùng peer_id nếu có
        peer_id = getattr(chat_widget, 'peer_id', None)
        if peer_id:
            return peer_id
        # Fallback về tên
        return getattr(chat_widget, 'contact_name', 'unknown')
    
    def add_chat(self, name, last_message, time_str, unread_count=0, selected=False):
        """Helper to append chat items via parent widget."""
        parent = self.chat_list_widget.parent()
        if hasattr(parent, 'add_chat'):
            parent.add_chat(name, last_message, time_str, unread_count, selected)
            self._cache_all_chat_items()
    
    def clear_selection(self):
        """Xóa selection hiện tại"""
        if self.current_chat_item:
            try:
                # Kiểm tra item còn tồn tại trong list
                row = self.chat_list_widget.row(self.current_chat_item)
                if row >= 0:
                    old_widget = self.chat_list_widget.itemWidget(self.current_chat_item)
                    if old_widget and hasattr(old_widget, 'set_selected'):
                        old_widget.set_selected(False)
            except (RuntimeError, AttributeError):
                # Item đã bị xóa, bỏ qua
                pass
            finally:
                self.current_chat_item = None
    
    def get_current_chat_info(self):
        """Lấy thông tin chat đang selected"""
        if not self.current_chat_item:
            return None
        
        try:
            # Kiểm tra item còn tồn tại trong list
            row = self.chat_list_widget.row(self.current_chat_item)
            if row < 0:
                self.current_chat_item = None
                return None
        except (RuntimeError, AttributeError):
            # Item đã bị xóa
            self.current_chat_item = None
            return None
        
        chat_widget = self.chat_list_widget.itemWidget(self.current_chat_item)
        if not chat_widget:
            return None
        
        return {
            'id': self._get_chat_id(chat_widget),
            'name': getattr(chat_widget, 'contact_name', ''),
            'last_message': getattr(chat_widget, 'last_message', ''),
            'time': getattr(chat_widget, 'time_label', ''),
            'unread_count': getattr(chat_widget, 'unread_count', 0)
        }

    def set_peer_refresh_handler(self, handler):
        """Đăng ký callback để trigger refresh danh sách peer từ Core."""
        self._peer_refresh_handler = handler

    def request_peer_refresh(self):
        if self._peer_refresh_handler:
            self._peer_refresh_handler()
    