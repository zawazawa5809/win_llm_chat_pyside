"""
MainWindow と SettingsDialog を提供する GUI モジュール。
"""

from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QPlainTextEdit, QPushButton, QMenuBar,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QCheckBox,
    QMessageBox
)
from PySide6.QtCore import Qt, QObject, QEvent, QThread
from PySide6.QtGui import QTextCursor

from .models import Message
from .config import Config, load_config, save_config
from .client import OpenAiCompatibleClient, LlmClientError
from .workers import ChatWorker, StreamChatWorker


class MainWindow(QMainWindow):
    """メインウィンドウ。チャット表示、入力、送信を管理する。"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LLM Chat Client")
        self.resize(800, 600)
        
        # 内部状態
        self.messages: list[Message] = []
        self.config = load_config()
        self.llm_client: Optional[OpenAiCompatibleClient] = None
        self._sending: bool = False
        self._worker_thread: Optional[QThread] = None
        self._worker: Optional[QObject] = None
        self._stop_button: Optional[QPushButton] = None
        self._initialize_client()
        
        # UI構築
        self._setup_ui()
        self._setup_menu()
        self._apply_markdown_style()
        
    def _initialize_client(self):
        """設定から LLM クライアントを初期化する。"""
        is_valid, error_msg = self.config.validate()
        if is_valid:
            # timeout は秒または (connect, read) 秒タプルで渡す
            # ストリーミング個別設定がある場合はそれを優先
            connect_ms = getattr(self.config, "stream_connect_timeout_ms", self.config.connect_timeout_ms)
            total_ms = getattr(self.config, "stream_total_timeout_ms", self.config.request_timeout_ms)
            connect_s = max(0.1, connect_ms / 1000.0)
            read_s = max(0.1, total_ms / 1000.0)
            self.llm_client = OpenAiCompatibleClient(
                base_url=self.config.base_url,
                model=self.config.model,
                api_key=self.config.api_key,
                timeout=(connect_s, read_s)
            )
        else:
            self.llm_client = None
        
    def _setup_ui(self):
        """UI コンポーネントを配置する。"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # チャット表示エリア（Markdown 対応）
        self.chat_view = QTextBrowser()
        self.chat_view.setMarkdown("# LLM Chat Client\n\nメッセージを入力して送信してください。")
        layout.addWidget(self.chat_view, stretch=3)
        
        # 入力エリア
        input_layout = QHBoxLayout()
        
        self.input_field = QPlainTextEdit()
        self.input_field.setPlaceholderText("メッセージを入力...")
        self.input_field.setMaximumHeight(100)
        # Enter 改行 / Ctrl+Enter 送信
        self.input_field.installEventFilter(self)
        input_layout.addWidget(self.input_field, stretch=4)
        
        self.send_button = QPushButton("送信")
        self.send_button.clicked.connect(self._on_send_clicked)
        input_layout.addWidget(self.send_button, stretch=1)

        # 応答停止ボタン（任意）。最初は無効化
        self._stop_button = QPushButton("停止")
        self._stop_button.setEnabled(False)
        self._stop_button.clicked.connect(self._on_stop_clicked)
        input_layout.addWidget(self._stop_button)
        
        layout.addLayout(input_layout)

        # ステータスバー（簡易インジケータ）
        self.statusBar().showMessage("")
        
    def _setup_menu(self):
        """メニューバーを設定する。"""
        menubar = self.menuBar()
        settings_menu = menubar.addMenu("設定")
        
        settings_action = settings_menu.addAction("接続設定...")
        settings_action.triggered.connect(self._open_settings_dialog)
        
    def _on_send_clicked(self):
        """送信ボタンがクリックされたときの処理。"""
        if self._sending:
            return

        user_input = self.input_field.toPlainText().strip()
        if not user_input:
            return
        
        # クライアントが初期化されていない場合
        if not self.llm_client:
            QMessageBox.warning(
                self,
                "設定エラー",
                "LLM クライアントが設定されていません。\n"
                "「設定」メニューから接続設定を確認してください。"
            )
            return
        
        # 送信中は UI を無効化＋インジケータ表示
        self._set_busy(True)
        
        # ユーザーメッセージを追加
        user_message = Message(role="user", content=user_input)
        self.messages.append(user_message)

        # ビュー更新（ユーザーメッセージ）＋自動スクロール
        self._update_chat_view()
        self._scroll_to_end()

        # アシスタント空メッセージを先行追加（逐次追記の受け皿）
        assistant_placeholder = Message(role="assistant", content="")
        self.messages.append(assistant_placeholder)
        self._update_chat_view()
        self._scroll_to_end()

        # ストリーミング Worker 起動
        self._start_stream_worker()
    
    def _update_chat_view(self):
        """メッセージリストから Markdown を生成してビューを更新する。"""
        markdown_parts = ["# LLM Chat Client\n"]
        
        for msg in self.messages:
            if msg.role == "user":
                markdown_parts.append(f"\n**User:**\n\n{msg.content}\n")
            elif msg.role == "assistant":
                markdown_parts.append(f"\n**Assistant:**\n\n{msg.content}\n")
        
        self.chat_view.setMarkdown("".join(markdown_parts))

    def _scroll_to_end(self):
        """ビュー末尾へスクロールする。"""
        cursor = self.chat_view.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_view.setTextCursor(cursor)
        self.chat_view.ensureCursorVisible()

    def _apply_markdown_style(self):
        """Markdown 表示の基本スタイルを適用する。"""
        ff = self.config.ui_markdown_font_family or "Segoe UI"
        fs = self.config.ui_markdown_font_size_pt or 11
        lh = self.config.ui_markdown_line_height or 1.6
        # Qt のスタイルシートは限定的だが、基本的な要素には適用できる。
        self.chat_view.setStyleSheet(
            "QTextBrowser {"
            f"  font-family: '{ff}';"
            f"  font-size: {fs}pt;"
            "}"
            "pre, code {"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  background: #f6f8fa;"
            "  border: 1px solid #e1e4e8;"
            "  border-radius: 4px;"
            "  padding: 4px;"
            "}"
            "pre {"
            "  padding: 8px;"
            "  margin: 6px 0;"
            "}"
            "table {"
            "  border-collapse: collapse;"
            "  margin: 6px 0;"
            "}"
            "th, td {"
            "  border: 1px solid #d0d7de;"
            "  padding: 4px 6px;"
            "}"
        )
        
    def _open_settings_dialog(self):
        """設定ダイアログを開く。"""
        dialog = SettingsDialog(self, self.config)
        if dialog.exec() == QDialog.Accepted:
            # 設定を保存
            self.config = dialog.get_config()
            save_config(self.config)
            
            # クライアントを再初期化
            self._initialize_client()
            
            QMessageBox.information(self, "設定", "設定が保存されました。")

    def _set_busy(self, busy: bool):
        """送信中 UI ロックとインジケータ制御。"""
        self._sending = busy
        self.send_button.setEnabled(not busy)
        self.input_field.setEnabled(not busy)
        if self._stop_button:
            # 停止ボタンは busy 中のみ有効（設定で制御）
            self._stop_button.setEnabled(bool(busy and getattr(self.config, "ui_streaming_stop_enabled", True)))
        if busy:
            self.statusBar().showMessage("応答待ち…")
            self.send_button.setText("送信中…")
        else:
            self.statusBar().clearMessage()
            self.send_button.setText("送信")

    def _start_worker(self):
        """バックグラウンド送信を開始する。"""
        # スナップショットを渡す（同時送信は許容しない）
        messages_snapshot = list(self.messages)

        self._worker_thread = QThread(self)
        self._worker = ChatWorker(self.llm_client, messages_snapshot)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.succeeded.connect(self._on_worker_succeeded)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.succeeded.connect(self._cleanup_worker)
        self._worker.failed.connect(self._cleanup_worker)
        self._worker_thread.start()

    def _cleanup_worker(self, *args):
        """ワーカー終了時のクリーンアップ。"""
        try:
            if self._worker_thread and self._worker_thread.isRunning():
                self._worker_thread.quit()
                self._worker_thread.wait(2000)
        finally:
            self._worker_thread = None
            self._worker = None
            self._set_busy(False)
            # UI 再有効化後にフォーカスを入力欄へ戻す
            self.input_field.setFocus()

    # Streaming 用
    def _start_stream_worker(self):
        """バックグラウンドでストリーミング送信を開始する。"""
        messages_snapshot = list(self.messages)
        self._worker_thread = QThread(self)
        worker = StreamChatWorker(self.llm_client, messages_snapshot)  # type: ignore[arg-type]
        self._worker = worker
        worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(worker.run)
        worker.stream_chunk.connect(self._on_stream_chunk)
        worker.stream_finished.connect(self._on_stream_finished)
        worker.failed.connect(self._on_worker_failed)
        worker.stream_finished.connect(self._cleanup_worker)
        worker.failed.connect(self._cleanup_worker)
        self._worker_thread.start()

    def _on_stream_chunk(self, delta: str):
        """ストリームのチャンクをアシスタント最新メッセージへ追記する。"""
        if not self.messages or self.messages[-1].role != "assistant":
            # 想定外だが安全側で補正
            self.messages.append(Message(role="assistant", content=""))
        self.messages[-1].content += delta
        self._update_chat_view()
        if self.config.ui_autoscroll_enabled:
            self._scroll_to_end()

    def _on_stream_finished(self, elapsed_ms: int):
        print(f"[stream] finished in {elapsed_ms} ms")
        self.input_field.clear()

    def _on_stop_clicked(self):
        """停止ボタン押下でストリームを中断する。"""
        try:
            # StreamChatWorker にだけ存在
            if hasattr(self._worker, "cancel"):
                getattr(self._worker, "cancel")()
        except Exception:
            pass

    # Worker コールバック
    def _on_worker_succeeded(self, content: str, elapsed_ms: int):
        print(f"[send] succeeded in {elapsed_ms} ms")
        assistant_message = Message(role="assistant", content=content)
        self.messages.append(assistant_message)
        self._update_chat_view()
        if self.config.ui_autoscroll_enabled:
            self._scroll_to_end()
        self.input_field.clear()

    def _on_worker_failed(self, user_message: str, detail: str, elapsed_ms: int):
        print(f"[send] failed in {elapsed_ms} ms: {detail}")
        QMessageBox.critical(self, "通信エラー", user_message)

    # キーバインド（Enter 改行 / Ctrl+Enter 送信）
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt 既定名
        if obj is self.input_field and event.type() == QEvent.KeyPress:
            key_event = event  # type: ignore[assignment]
            key = key_event.key()
            mods = key_event.modifiers()
            # Shift+Enter は常に改行
            if (mods & Qt.ShiftModifier) and key in (Qt.Key_Return, Qt.Key_Enter):
                return False
            # Ctrl+Enter で送信（設定有効時）
            if self.config.ui_ctrl_enter_to_send and (mods & Qt.ControlModifier) and key in (Qt.Key_Return, Qt.Key_Enter):
                self._on_send_clicked()
                return True
            # Enter で送信（設定有効時、修飾なし）
            if self.config.ui_enter_to_send and (mods == Qt.NoModifier) and key in (Qt.Key_Return, Qt.Key_Enter):
                self._on_send_clicked()
                return True
        return super().eventFilter(obj, event)


class SettingsDialog(QDialog):
    """接続設定を編集するダイアログ。"""
    
    def __init__(self, parent=None, config: Optional[Config] = None):
        super().__init__(parent)
        self.setWindowTitle("接続設定")
        self.resize(400, 200)
        
        layout = QFormLayout(self)
        
        # 設定項目
        self.base_url_field = QLineEdit()
        self.base_url_field.setPlaceholderText("http://localhost:11434")
        if config:
            self.base_url_field.setText(config.base_url)
        layout.addRow("ベース URL:", self.base_url_field)
        
        self.model_field = QLineEdit()
        self.model_field.setPlaceholderText("gemma3:4b")
        if config:
            self.model_field.setText(config.model)
        layout.addRow("モデル名:", self.model_field)
        
        self.api_key_field = QLineEdit()
        self.api_key_field.setEchoMode(QLineEdit.Password)
        self.api_key_field.setPlaceholderText("（任意）")
        if config and config.api_key:
            self.api_key_field.setText(config.api_key)
        layout.addRow("API キー:", self.api_key_field)

        # タイムアウト（秒）
        self.timeout_field = QLineEdit()
        if config:
            self.timeout_field.setText(str(int(config.request_timeout_ms / 1000)))
        else:
            self.timeout_field.setText("30")
        layout.addRow("リードタイムアウト（秒）:", self.timeout_field)

        # 送信キーバインド
        self.ctrl_enter_checkbox = QCheckBox("Ctrl+Enter で送信")
        self.enter_to_send_checkbox = QCheckBox("Enter で送信")
        if config:
            self.ctrl_enter_checkbox.setChecked(bool(config.ui_ctrl_enter_to_send))
            self.enter_to_send_checkbox.setChecked(bool(config.ui_enter_to_send))
        else:
            self.ctrl_enter_checkbox.setChecked(True)
            self.enter_to_send_checkbox.setChecked(False)
        layout.addRow(self.ctrl_enter_checkbox)
        layout.addRow(self.enter_to_send_checkbox)
        
        # ボタン
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
    
    def _on_accept(self):
        """OK ボタンが押されたときのバリデーション。"""
        config = self.get_config()
        is_valid, error_msg = config.validate()
        
        if not is_valid:
            QMessageBox.warning(self, "入力エラー", error_msg)
            return
        
        self.accept()
    
    def get_config(self) -> Config:
        """ダイアログの入力から Config を生成する。"""
        api_key = self.api_key_field.text().strip()
        # タイムアウトは整数秒を ms に変換。無効入力は既定 30s を採用。
        try:
            read_timeout_s = max(1, int(self.timeout_field.text().strip()))
        except ValueError:
            read_timeout_s = 30
        # キーバインドは片方のみ有効にする（両方ONの場合は Ctrl+Enter 優先）
        ctrl_enter = self.ctrl_enter_checkbox.isChecked()
        enter_send = self.enter_to_send_checkbox.isChecked() and not ctrl_enter
        return Config(
            base_url=self.base_url_field.text().strip(),
            model=self.model_field.text().strip(),
            api_key=api_key if api_key else None,
            request_timeout_ms=read_timeout_s * 1000,
            ui_ctrl_enter_to_send=ctrl_enter,
            ui_enter_to_send=enter_send
        )


