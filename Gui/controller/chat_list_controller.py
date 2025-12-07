from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QListWidgetItem
from Gui.view.chat_item import ChatItemWidget

class ChatListController(QObject):
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
        
        self._connect_signals()
    
    def _connect_signals(self):
        
        self.chat_list_widget.itemClicked.connect(self._on_chat_item_clicked)
        
        self.chat_list_widget.itemDoubleClicked.connect(self._on_chat_item_double_clicked)
    
    def set_search_input(self, search_input):
        
        self.search_input = search_input
        if self.search_input:
            self.search_input.textChanged.connect(self._on_search_text_changed)
    
    def set_tab_labels(self, direct_tab, groups_tab, public_tab):
        
        self.tab_labels = {
            "DIRECT": direct_tab,
            "GROUPS": groups_tab,
            "PUBLIC": public_tab
        }
        
        for tab_name, tab_label in self.tab_labels.items():
            tab_label.mousePressEvent = self._create_tab_click_handler(tab_name)
    
    def _create_tab_click_handler(self, tab_name):
        
        def handler(event):
            if event.button() == Qt.LeftButton:
                self.switch_tab(tab_name)
        return handler
    
    def switch_tab(self, tab_name):
        
        if tab_name not in self.tab_labels or tab_name == self.current_tab:
            return
        
        old_tab = self.tab_labels[self.current_tab]
        old_tab.setObjectName("TabLabel")
        old_tab.style().unpolish(old_tab)
        old_tab.style().polish(old_tab)
        
        new_tab = self.tab_labels[tab_name]
        new_tab.setObjectName("TabLabelActive")
        new_tab.style().unpolish(new_tab)
        new_tab.style().polish(new_tab)
        
        self.current_tab = tab_name

        self._filter_chats_by_tab(tab_name)

        self.tab_changed.emit(tab_name)
        self.request_peer_refresh()

    def _filter_chats_by_tab(self, tab_name):
        
        pass

    def _on_search_text_changed(self, text):
        
        search_text = text.strip().lower()
        self._filter_chats(search_text)
        self.search_performed.emit(search_text)
    
    def _filter_chats(self, search_text):
        
        if not self.all_chat_items:
            self._cache_all_chat_items()
        
        if not search_text:
            self._show_all_chats()
            return
        
        for i in range(self.chat_list_widget.count()):
            self.chat_list_widget.item(i).setHidden(True)
        
        for list_item, chat_data in self.all_chat_items:
            chat_widget = self.chat_list_widget.itemWidget(list_item)
            if chat_widget and self._chat_matches_search(chat_widget, search_text):
                list_item.setHidden(False)
    
    def _cache_all_chat_items(self):
        
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
        
        contact_name = getattr(chat_widget, 'contact_name', '').lower()
        if search_text in contact_name:
            return True
        
        last_message = getattr(chat_widget, 'last_message', '').lower()
        if search_text in last_message:
            return True
        
        return False
    
    def _show_all_chats(self):
        
        for list_item, _ in self.all_chat_items:
            list_item.setHidden(False)
    
    def _on_chat_item_clicked(self, item):
        
        if not item:
            return
            
        chat_widget = self.chat_list_widget.itemWidget(item)
        if not chat_widget:
            return
        
        if self.current_chat_item:
            try:
                row = self.chat_list_widget.row(self.current_chat_item)
                if row >= 0:
                    old_widget = self.chat_list_widget.itemWidget(self.current_chat_item)
                    if old_widget and hasattr(old_widget, 'set_selected'):
                        old_widget.set_selected(False)
            except (RuntimeError, AttributeError):
                self.current_chat_item = None
        
        if hasattr(chat_widget, 'set_selected'):
            chat_widget.set_selected(True)
        
        self.current_chat_item = item
        
        chat_id = self._get_chat_id(chat_widget)
        chat_name = getattr(chat_widget, 'contact_name', '')
        
        self.chat_selected.emit(chat_id, chat_name)
    
    def _on_chat_item_double_clicked(self, item):
        
        chat_widget = self.chat_list_widget.itemWidget(item)
        if chat_widget:
            pass
    
    def _get_chat_id(self, chat_widget):
        
        peer_id = getattr(chat_widget, 'peer_id', None)
        if peer_id:
            return peer_id
        return getattr(chat_widget, 'contact_name', 'unknown')
    
    def add_chat(self, name, last_message, time_str, unread_count=0, selected=False):
        
        parent = self.chat_list_widget.parent()
        if hasattr(parent, 'add_chat'):
            parent.add_chat(name, last_message, time_str, unread_count, selected)
            self._cache_all_chat_items()
    
    def clear_selection(self):
        
        if self.current_chat_item:
            try:
                row = self.chat_list_widget.row(self.current_chat_item)
                if row >= 0:
                    old_widget = self.chat_list_widget.itemWidget(self.current_chat_item)
                    if old_widget and hasattr(old_widget, 'set_selected'):
                        old_widget.set_selected(False)
            except (RuntimeError, AttributeError):
                pass
            finally:
                self.current_chat_item = None
    
    def get_current_chat_info(self):
        
        if not self.current_chat_item:
            return None
        
        try:
            row = self.chat_list_widget.row(self.current_chat_item)
            if row < 0:
                self.current_chat_item = None
                return None
        except (RuntimeError, AttributeError):
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
        
        self._peer_refresh_handler = handler

    def request_peer_refresh(self):
        if self._peer_refresh_handler:
            self._peer_refresh_handler()
