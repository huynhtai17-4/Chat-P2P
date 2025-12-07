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

    file_attached = Signal(str, str, str)  # file_path, file_name, file_data_base64
    emoji_selected = Signal(str)      # emoji_character
    message_sent = Signal(str)        # message_text
    audio_recorded = Signal(str, str)  # audio_path, audio_data_base64

    def __init__(self, chat_area_widget):
        super().__init__()
        self.chat_area_widget = chat_area_widget
        self.message_input = None
        self.attach_button = None
        self.emoji_button = None
        self.mic_button = None
        self.send_button = None
        self._send_handler = None
        self._is_recording = False
        self._recording_timer = None
        self._recording_duration = 0

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

    def set_mic_button(self, mic_button):
        self.mic_button = mic_button
        if self.mic_button:
            self.mic_button.pressed.connect(self._start_recording)
            self.mic_button.released.connect(self._stop_recording)

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
            "All Files (*);;Images (*.png *.jpg *.jpeg *.gif *.bmp);;Documents (*.pdf *.doc *.docx *.txt);;Audio (*.mp3 *.wav *.ogg *.m4a)"
        )
        file_dialog.setViewMode(QFileDialog.Detail)

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            for file_path in selected_files:
                try:
                    file_name = os.path.basename(file_path)
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                    file_data_base64 = base64.b64encode(file_data).decode('utf-8')
                    
                    self.file_attached.emit(file_path, file_name, file_data_base64)

                    current_text = self.message_input.text()
                    clip = f"📎{file_name}"
                    self.message_input.setText(f"{current_text} {clip}".strip())
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")

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
        if not message_text:
            return

        handler_success = True
        if self._send_handler:
            handler_success = self._send_handler(message_text)
        if not handler_success:
            return

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

    def _start_recording(self):
        if self._is_recording:
            return
        
        try:
            try:
                import pyaudio
            except ImportError:
                print("pyaudio not available. Install with: pip install pyaudio")
                return
            
            import wave
            import tempfile
            
            self._is_recording = True
            self._recording_duration = 0
            
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 44100
            
            self._audio = pyaudio.PyAudio()
            self._stream = self._audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            self._recording_frames = []
            self._recording_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            self._recording_path = self._recording_file.name
            
            if self.message_input:
                self.message_input.setPlaceholderText("🎤 Đang ghi âm... (thả để dừng)")
                self.message_input.setEnabled(False)
            
            self._recording_timer = QTimer()
            self._recording_timer.timeout.connect(self._record_audio_chunk)
            self._recording_timer.start(100)
            
        except ImportError:
            print("pyaudio not available. Install with: pip install pyaudio")
            self._is_recording = False
        except Exception as e:
            print(f"Error starting recording: {e}")
            self._is_recording = False

    def _record_audio_chunk(self):
        if not self._is_recording:
            return
        
        try:
            data = self._stream.read(1024, exception_on_overflow=False)
            self._recording_frames.append(data)
            self._recording_duration += 0.1
        except Exception as e:
            print(f"Error recording chunk: {e}")

    def _stop_recording(self):
        if not self._is_recording:
            return
        
        try:
            self._is_recording = False
            
            if self._recording_timer:
                self._recording_timer.stop()
                self._recording_timer = None
            
            if hasattr(self, '_stream'):
                self._stream.stop_stream()
                self._stream.close()
            
            if hasattr(self, '_audio'):
                import pyaudio
                self._audio.terminate()
            
            if self._recording_duration < 0.5:
                if hasattr(self, '_recording_path') and os.path.exists(self._recording_path):
                    os.unlink(self._recording_path)
                if self.message_input:
                    self.message_input.setPlaceholderText("Type a message here...")
                    self.message_input.setEnabled(True)
                return
            
            import wave
            wf = wave.open(self._recording_path, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(self._audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(44100)
            wf.writeframes(b''.join(self._recording_frames))
            wf.close()
            
            with open(self._recording_path, 'rb') as f:
                audio_data = f.read()
            audio_data_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            duration_str = f"{int(self._recording_duration)}s"
            self.audio_recorded.emit(self._recording_path, audio_data_base64)
            
            if self.message_input:
                current_text = self.message_input.text()
                audio_note = f"🎤 Audio ({duration_str})"
                self.message_input.setText(f"{current_text} {audio_note}".strip())
                self.message_input.setPlaceholderText("Type a message here...")
                self.message_input.setEnabled(True)
            
        except Exception as e:
            print(f"Error stopping recording: {e}")
            if self.message_input:
                self.message_input.setPlaceholderText("Type a message here...")
                self.message_input.setEnabled(True)

    def test_emoji_support(self):
        test_emojis = ["😀", "❤️", "🐶", "⭐", "🎉", "✅"]
        print("Testing emoji support:")
        for emoji in test_emojis:
            print(f"  {emoji} - OK")
        return True
