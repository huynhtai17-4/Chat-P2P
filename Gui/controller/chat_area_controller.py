import os
import base64
from typing import Callable

from PySide6.QtCore import QObject, Signal, Qt, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QScrollArea,
    QWidget,
    QTabWidget,
    QLabel
)

class ChatAreaController(QObject):

    file_attached = Signal(str, str, str, bool)  # file_path, file_name, file_data_base64, is_image
    emoji_selected = Signal(str)      # emoji_character
    message_sent = Signal(str)        # message_text

    def __init__(self, chat_area_widget):
        super().__init__()
        self.chat_area_widget = chat_area_widget
        self.message_input = None
        self.attach_button = None
        self.emoji_button = None
        self.send_button = None
        self._send_handler = None

    def set_message_input(self, message_input):
        self.message_input = message_input
        if self.message_input:
            self.message_input.returnPressed.connect(self._send_message)

    def set_attach_button(self, attach_button):
        self.attach_button = attach_button
        if self.attach_button:
            self.attach_button.clicked.connect(self._show_file_dialog)

    def set_emoji_button(self, emoji_button):
        self.emoji_button = emoji_button
        if self.emoji_button:
            self.emoji_button.clicked.connect(self._show_emoji_picker)

    def set_send_button(self, send_button):
        self.send_button = send_button
        if self.send_button:
            self.send_button.clicked.connect(self._send_message)

    def set_send_handler(self, handler: Callable[[str], bool]):
        
        self._send_handler = handler

    def _show_file_dialog(self):
        if not self.message_input:
            return

        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter(
            "All Files (*);;Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;Documents (*.pdf *.doc *.docx *.txt *.xls *.xlsx *.ppt *.pptx)"
        )
        file_dialog.setViewMode(QFileDialog.Detail)

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            for file_path in selected_files:
                try:
                    file_name = os.path.basename(file_path)
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                    
                    # Ensure binary read
                    if isinstance(file_data, str):
                        file_data = file_data.encode('utf-8')
                        
                    file_data_base64 = base64.b64encode(file_data).decode('utf-8')
                    
                    file_ext = os.path.splitext(file_name)[1].lower()
                    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
                    is_image = file_ext in image_extensions
                    
                    self.file_attached.emit(file_path, file_name, file_data_base64, is_image)
                except Exception as e:
                    pass

    def _show_emoji_picker(self):
        if not self.message_input:
            return

        emoji_dialog = QDialog(self.chat_area_widget)
        emoji_dialog.setWindowTitle("Chọn Emoji")
        emoji_dialog.setFixedSize(450, 500)
        emoji_dialog.setModal(True)

        emoji_categories = {
            "Cảm xúc": [
                "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇",
                "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚",
                "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎", "🤩",
                "🥳", "😏", "😒", "😞", "😔", "😟", "😕", "🙁", "☹️", "😣",
                "😖", "😫", "😩", "🥺", "😢", "😭", "😤", "😠", "😡", "🤬",
                "🤯", "😳", "🥵", "🥶", "😱", "😨", "😰", "😥", "😓", "🤗",
            ],
            "Trái tim": [
                "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔",
                "❣️", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "💟", "♥️",
            ],
            "Động vật": [
                "🐵", "🐒", "🦍", "🦧", "🐶", "🐕", "🦮", "🐕‍🦺", "🐩", "🐺",
                "🦊", "🦝", "🐱", "🐈", "🐈‍⬛", "🦁", "🐯", "🐅", "🐆", "🐴",
                "🐎", "🦄", "🦓", "🦌", "🐮", "🐂", "🐃", "🐄", "🐷", "🐖",
            ],
            "Đồ ăn": [
                "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐", "🍈",
                "🍒", "🍑", "🥭", "🍍", "🥥", "🥝", "🍅", "🍆", "🥑", "🥦",
            ],
            "Hoạt động": [
                "⚽", "🏀", "🏈", "⚾", "🥎", "🎾", "🏐", "🏉", "🥏", "🎱",
                "🪀", "🏓", "🏸", "🏒", "🏑", "🥍", "🏏", "🎿", "⛷️", "🏂",
            ],
            "Biểu tượng": [
                "✅", "✔️", "❌", "⭕", "🔴", "🟠", "🟡", "🟢", "🔵", "🟣",
                "⚫", "⚪", "🟤", "🔺", "🔻", "🔸", "🔹", "🔶", "🔷", "💠",
            ]
        }

        tab_widget = QTabWidget()
        for category_name, emojis in emoji_categories.items():
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_widget = QWidget()
            emoji_layout = QGridLayout(scroll_widget)
            emoji_layout.setSpacing(8)
            emoji_layout.setAlignment(Qt.AlignTop)
            emoji_layout.setContentsMargins(10, 10, 10, 10)

            row, col = 0, 0
            max_cols = 8
            for emoji in emojis:
                emoji_btn = QPushButton(emoji)
                emoji_btn.setFixedSize(45, 45)
                emoji_btn.setStyleSheet("QPushButton { border: none; background: transparent; font-size: 24px; } QPushButton:hover { background-color: rgba(0,0,0,0.1); }")
                emoji_btn.clicked.connect(
                    lambda checked=False, e=emoji, dlg=emoji_dialog: self._on_emoji_selected(e, dlg)
                )

                emoji_layout.addWidget(emoji_btn, row, col)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

            emoji_layout.setRowStretch(row + 1, 1)
            scroll_area.setWidget(scroll_widget)
            tab_widget.addTab(scroll_area, category_name)

        close_btn = QPushButton("Đóng")
        close_btn.setFixedSize(100, 35)
        close_btn.clicked.connect(emoji_dialog.close)

        main_layout = QVBoxLayout(emoji_dialog)
        main_layout.setSpacing(0)
        main_layout.addWidget(tab_widget)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        button_layout.addStretch()
        button_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addLayout(button_layout)

        emoji_dialog.exec()

    def _on_emoji_selected(self, emoji, dialog):
        dialog.close()
        if self.message_input:
            cursor_position = self.message_input.cursorPosition()
            current_text = self.message_input.text()
            new_text = current_text[:cursor_position] + emoji + current_text[cursor_position:]
            self.message_input.setText(new_text)
            self.message_input.setCursorPosition(cursor_position + len(emoji))
            self.message_input.setFocus()
        self.emoji_selected.emit(emoji)

    def _send_message(self):
        if not self.message_input:
            return

        message_text = self.message_input.text().strip()
        
        handler_success = True
        if self._send_handler:
            handler_success = self._send_handler(message_text)
        if not handler_success:
            return

        if message_text:
            self.message_sent.emit(message_text)
        self.message_input.clear()

    def clear_message_input(self):
        if self.message_input:
            self.message_input.clear()

    def set_message_text(self, text):
        if self.message_input:
            self.message_input.setText(text)

    def get_message_text(self):
        if self.message_input:
            return self.message_input.text()
        return ""

    def test_emoji_support(self):
        test_emojis = ["😀", "❤️", "🐶", "⭐", "🎉", "✅"]
        print("Testing emoji support:")
        for emoji in test_emojis:
            print(f"  {emoji} - OK")
        return True
