"""
MainWindow と SettingsDialog を提供する GUI モジュール。
"""

from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QPlainTextEdit, QPushButton, QMenuBar,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QCheckBox, QFileDialog,
    QMessageBox, QComboBox, QLabel
)
from PySide6.QtCore import Qt, QObject, QEvent, QThread, QUrl
from PySide6.QtGui import QTextCursor, QDesktopServices, QGuiApplication

from .models import Message
from .config import Config, load_config, save_config, get_default_history_path, get_current_profile, Profile, validate_profile
from .client import OpenAiCompatibleClient, LlmClientError
from .workers import ChatWorker, StreamChatWorker, LoadSessionWorker
from . import storage
from .factory import create_llm_client
from .app_logger import app_logger
from .diagnostics import DiagnosticsInfoProvider


class MainWindow(QMainWindow):
    """メインウィンドウ。チャット表示、入力、送信を管理する。"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LLM Chat Client")
        self.resize(800, 600)
        
        # 内部状態
        self.messages: list[Message] = []
        self.config = load_config()
        # ロガー初期化（Config 反映）
        try:
            app_logger.configure(self.config)
            app_logger.info("app.start", {"profile_name": self.config.current_profile_name or ""})
        except Exception:
            # ログ初期化失敗はアプリ動作のブロッカーにはしない
            pass
        self.llm_client: Optional[OpenAiCompatibleClient] = None
        self._sending: bool = False
        self._worker_thread: Optional[QThread] = None
        self._worker: Optional[QObject] = None
        self._io_thread: Optional[QThread] = None
        self._io_worker: Optional[QObject] = None
        self._stop_button: Optional[QPushButton] = None
        self._profile_combo: Optional[QComboBox] = None
        self._initialize_client()
        
        # UI構築
        self._setup_ui()
        self._setup_menu()
        self._apply_markdown_style()
        # 起動時ロード（設定が有効なら）
        self._load_session_if_available()
        
    def _initialize_client(self):
        """設定から LLM クライアントを初期化する。"""
        prof = get_current_profile(self.config)
        # 後方互換：プロファイルが未設定のケースも validate で弾かない
        is_valid, error_msg = self.config.validate()
        if not is_valid:
            self.llm_client = None
            return
        if prof:
            self.llm_client = create_llm_client(
                prof,
                connect_timeout_ms=getattr(self.config, "stream_connect_timeout_ms", self.config.connect_timeout_ms),
                total_timeout_ms=getattr(self.config, "stream_total_timeout_ms", self.config.request_timeout_ms),
            )  # type: ignore[assignment]
            return
        # 旧形式：Config の単一項目から OpenAI 互換クライアントを作成
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
        
    def _setup_ui(self):
        """UI コンポーネントを配置する。"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)

        # プロファイル選択バー
        top_bar = QHBoxLayout()
        label = QLabel("プロファイル:")
        self._profile_combo = QComboBox()
        self._refresh_profile_combo()
        self._profile_combo.currentTextChanged.connect(self._on_profile_selected)
        top_bar.addWidget(label)
        top_bar.addWidget(self._profile_combo, stretch=1)
        layout.addLayout(top_bar)
        
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
        file_menu = menubar.addMenu("ファイル")
        export_action = file_menu.addAction("この会話をMarkdownで保存…")
        export_action.triggered.connect(self._export_markdown_dialog)

        settings_menu = menubar.addMenu("設定")

        settings_action = settings_menu.addAction("プロファイル設定...")
        settings_action.triggered.connect(self._open_settings_dialog)

        logging_action = settings_menu.addAction("ログ/診断設定...")
        logging_action.triggered.connect(self._open_logging_settings_dialog)

        help_menu = menubar.addMenu("ヘルプ")
        logs_action = help_menu.addAction("ログフォルダを開く")
        logs_action.triggered.connect(self._open_logs_folder)
        diag_action = help_menu.addAction("診断情報...")
        diag_action.triggered.connect(self._show_diagnostics_dialog)

    def _refresh_profile_combo(self) -> None:
        if not self._profile_combo:
            return
        self._profile_combo.blockSignals(True)
        self._profile_combo.clear()
        names = [p.name for p in (self.config.profiles or [])]
        self._profile_combo.addItems(names)
        current = self.config.current_profile_name or (names[0] if names else "")
        if current:
            idx = self._profile_combo.findText(current)
            if idx >= 0:
                self._profile_combo.setCurrentIndex(idx)
        self._profile_combo.blockSignals(False)

    def _on_profile_selected(self, name: str) -> None:
        """ドロップダウンでプロファイルが選択されたときの処理。"""
        if not name:
            return
        if name == self.config.current_profile_name:
            return
        # 送信中は切替禁止
        if self._sending:
            QMessageBox.information(self, "切替", "送信中はプロファイルを切り替えられません。")
            self._refresh_profile_combo()
            return
        # 反映
        self.config.current_profile_name = name
        save_config(self.config)
        # ロガーの設定も更新
        try:
            app_logger.configure(self.config)
            app_logger.info("config.profile_changed", {"profile_name": name})
        except Exception:
            pass
        self._initialize_client()
        self.statusBar().showMessage(f"プロファイルを切り替えました: {name}", 3000)
        
    def _on_send_clicked(self):
        """送信ボタンがクリックされたときの処理。"""
        if self._sending:
            return

        # 履歴のサイズ警告（非ブロッキング）
        self._check_history_limits()

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
        """プロファイル設定ダイアログを開く。"""
        dialog = SettingsDialog(self, self.config)
        if dialog.exec() == QDialog.Accepted:
            # 更新後の config を取得・保存
            self.config = dialog.get_config()
            save_config(self.config)
            try:
                app_logger.configure(self.config)
                app_logger.info("config.updated", {"profile_name": self.config.current_profile_name or ""})
            except Exception:
                pass
            # ドロップダウン更新とクライアント再初期化
            self._refresh_profile_combo()
            self._initialize_client()

            QMessageBox.information(self, "設定", "プロファイル設定を保存しました。")

    def _open_logging_settings_dialog(self) -> None:
        """ログ/診断設定ダイアログを開く。"""
        dialog = LoggingSettingsDialog(self, self.config)
        if dialog.exec() == QDialog.Accepted:
            self.config = dialog.get_config()
            save_config(self.config)
            try:
                app_logger.configure(self.config)
                app_logger.info("config.logging_updated", {"logging_enabled": self.config.logging_enabled})
            except Exception:
                pass
            QMessageBox.information(self, "設定", "ログ/診断設定を保存しました。")

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
        try:
            app_logger.info(
                "chat.stream.finished",
                {
                    "elapsed_ms": elapsed_ms,
                    "profile_name": self.config.current_profile_name or "",
                },
            )
        except Exception:
            pass
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
        try:
            app_logger.info(
                "chat.send.succeeded",
                {
                    "elapsed_ms": elapsed_ms,
                    "profile_name": self.config.current_profile_name or "",
                },
            )
        except Exception:
            pass
        assistant_message = Message(role="assistant", content=content)
        self.messages.append(assistant_message)
        self._update_chat_view()
        if self.config.ui_autoscroll_enabled:
            self._scroll_to_end()
        self.input_field.clear()

    def _on_worker_failed(self, user_message: str, detail: str, elapsed_ms: int):
        try:
            app_logger.error(
                "chat.send.failed",
                {
                    "elapsed_ms": elapsed_ms,
                    "profile_name": self.config.current_profile_name or "",
                    "detail": detail,
                },
            )
        except Exception:
            pass
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

    # ---- v0.4: 履歴のロード/セーブ/エクスポート ----
    def _history_path(self) -> str:
        """履歴の保存先パス（文字列）を取得する。"""
        cfg_path = getattr(self.config, "history_path", None)
        if cfg_path:
            return cfg_path  # type: ignore[return-value]
        base = get_default_history_path()
        fmt = getattr(self.config, "history_format", "json")
        if fmt == "markdown":
            base = base.with_suffix(".md")
        return str(base)

    def _load_session_if_available(self) -> None:
        """起動時にセッションを自動ロードする（有効時）。"""
        if not getattr(self.config, "history_enabled", True):
            return
        from pathlib import Path as _P
        p = _P(self._history_path())
        if not p.exists():
            return
        # 非ブロッキングでロード
        self._io_thread = QThread(self)
        worker = LoadSessionWorker(p)
        self._io_worker = worker
        worker.moveToThread(self._io_thread)
        self._io_thread.started.connect(worker.run)
        worker.succeeded.connect(self._on_load_succeeded)
        worker.failed.connect(self._on_load_failed)
        worker.succeeded.connect(self._cleanup_io_worker)
        worker.failed.connect(self._cleanup_io_worker)
        self._io_thread.start()

    def _cleanup_io_worker(self, *args):
        try:
            if self._io_thread and self._io_thread.isRunning():
                self._io_thread.quit()
                self._io_thread.wait(2000)
        finally:
            self._io_thread = None
            self._io_worker = None

    def _on_load_succeeded(self, loaded_messages: list):
        try:
            if loaded_messages:
                # list[dict] の場合にも対応（安全側）
                msgs: list[Message] = []
                for item in loaded_messages:
                    if isinstance(item, Message):
                        msgs.append(item)
                    elif isinstance(item, dict):
                        msgs.append(Message.from_dict(item))
                if msgs:
                    self.messages = msgs
                    self._update_chat_view()
                    self.statusBar().showMessage("前回の会話を読み込みました", 3000)
        except Exception:
            QMessageBox.information(self, "履歴の読み込み", "前回の会話を読み込めませんでした。新規セッションで開始します。")

    def _on_load_failed(self, detail: str):
        QMessageBox.information(self, "履歴の読み込み", "前回の会話を読み込めませんでした。新規セッションで開始します。")

    def _check_history_limits(self) -> None:
        """履歴のソフト上限を超えた場合に非ブロッキングで通知する。"""
        max_msgs = int(getattr(self.config, "history_max_messages", 400) or 400)
        max_chars = int(getattr(self.config, "history_max_chars", 200000) or 200000)
        num_msgs, total_chars = storage.calculate_history_size(self.messages)
        if num_msgs > max_msgs or total_chars > max_chars:
            self.statusBar().showMessage("履歴が大きくなっています。保存/エクスポート前に見直しを検討してください。", 5000)

    def closeEvent(self, event):  # noqa: N802 - Qt 既定名
        """ウィンドウクローズ時にセッションを保存する。"""
        try:
            if getattr(self.config, "history_enabled", True):
                self._check_history_limits()
                from pathlib import Path as _P
                p = _P(self._history_path())
                fmt = getattr(self.config, "history_format", "json")
                if fmt == "markdown":
                    storage.export_markdown_file(self.messages, p, metadata={"model": self.config.model})
                else:
                    storage.save_session_atomic(self.messages, p)
        except Exception:
            QMessageBox.warning(self, "保存エラー", "セッションの保存に失敗しました。")
        finally:
            try:
                app_logger.info("app.exit", {"profile_name": self.config.current_profile_name or ""})
            except Exception:
                pass
            super().closeEvent(event)

    def _export_markdown_dialog(self) -> None:
        """Markdown エクスポートのためのファイル保存ダイアログを開く。"""
        default_dir = getattr(self.config, "export_default_dir", None)
        pattern = getattr(self.config, "export_filename_pattern", "Chat-{yyyy-MM-dd HH-mm}.md")
        from datetime import datetime
        safe_name = pattern.replace("{yyyy-MM-dd HH-mm}", datetime.now().strftime("%Y-%m-%d %H-%M"))
        initial_path = f"{default_dir or ''}/{safe_name}" if default_dir else safe_name
        path, _ = QFileDialog.getSaveFileName(self, "Markdown で保存", initial_path, "Markdown (*.md)")
        if not path:
            return
        try:
            meta = {"model": self.config.model}
            from pathlib import Path as _P
            storage.export_markdown_file(self.messages, _P(path), metadata=meta)
            self.statusBar().showMessage("Markdown を保存しました", 3000)
        except Exception as e:
            QMessageBox.warning(self, "エクスポート失敗", f"Markdown の保存に失敗しました:\n{e}")

    def _open_logs_folder(self) -> None:
        """ログフォルダを OS のファイルエクスプローラで開く。"""
        try:
            path = app_logger.get_log_dir()
            url = QUrl.fromLocalFile(str(path))
            if not QDesktopServices.openUrl(url):
                raise RuntimeError("ログフォルダを開けませんでした")
            app_logger.info("logs.opened", {"path": str(path)})
        except Exception as e:  # noqa: BLE001
            try:
                app_logger.error("logs.open_failed", {"error": str(e)})
            except Exception:
                pass
            QMessageBox.warning(self, "ログフォルダ", "ログフォルダを開けませんでした。")

    def _show_diagnostics_dialog(self) -> None:
        """診断情報ダイアログを表示する。"""
        provider = DiagnosticsInfoProvider(self.config)
        info = provider.collect()
        text = provider.format_text(info)
        try:
            app_logger.info("diagnostics.opened", {"profile_name": self.config.current_profile_name or ""})
        except Exception:
            pass

        dialog = QDialog(self)
        dialog.setWindowTitle("診断情報")
        layout = QVBoxLayout(dialog)

        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(text)
        layout.addWidget(text_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        copy_button = QPushButton("コピー")
        button_box.addButton(copy_button, QDialogButtonBox.ActionRole)
        button_box.rejected.connect(dialog.reject)

        def _copy() -> None:
            QGuiApplication.clipboard().setText(text_edit.toPlainText())

        copy_button.clicked.connect(_copy)
        layout.addWidget(button_box)

        dialog.exec()


class SettingsDialog(QDialog):
    """プロファイルを編集するダイアログ（追加/編集/削除）。"""
    
    def __init__(self, parent=None, config: Optional[Config] = None):
        super().__init__(parent)
        self.setWindowTitle("プロファイル設定")
        self.resize(420, 260)
        self._config = config or Config()
        
        layout = QFormLayout(self)
        
        # 設定項目（プロファイル名/タイプ）
        self.name_field = QLineEdit()
        current = get_current_profile(self._config)
        self.name_field.setText(current.name if current else "default")
        layout.addRow("プロファイル名:", self.name_field)

        self.type_field = QComboBox()
        self.type_field.addItems(["openai", "ollama"])
        if current:
            idx = self.type_field.findText(current.type)
            if idx >= 0:
                self.type_field.setCurrentIndex(idx)
        layout.addRow("タイプ:", self.type_field)

        # 接続項目
        self.base_url_field = QLineEdit()
        self.base_url_field.setPlaceholderText("http://localhost:11434")
        if current:
            self.base_url_field.setText(current.base_url)
        else:
            self.base_url_field.setText(self._config.base_url)
        layout.addRow("ベース URL:", self.base_url_field)
        
        self.model_field = QLineEdit()
        self.model_field.setPlaceholderText("gemma3:4b")
        if current:
            self.model_field.setText(current.model)
        else:
            self.model_field.setText(self._config.model)
        layout.addRow("モデル名:", self.model_field)
        
        self.api_key_field = QLineEdit()
        self.api_key_field.setEchoMode(QLineEdit.Password)
        self.api_key_field.setPlaceholderText("（任意）")
        if current and current.api_key:
            self.api_key_field.setText(current.api_key)
        elif self._config.api_key:
            self.api_key_field.setText(self._config.api_key)
        layout.addRow("API キー:", self.api_key_field)

        # タイムアウト（秒）
        self.timeout_field = QLineEdit()
        if self._config:
            self.timeout_field.setText(str(int(self._config.request_timeout_ms / 1000)))
        else:
            self.timeout_field.setText("30")
        layout.addRow("リードタイムアウト（秒）:", self.timeout_field)

        # 送信キーバインド
        self.ctrl_enter_checkbox = QCheckBox("Ctrl+Enter で送信")
        self.enter_to_send_checkbox = QCheckBox("Enter で送信")
        if self._config:
            self.ctrl_enter_checkbox.setChecked(bool(self._config.ui_ctrl_enter_to_send))
            self.enter_to_send_checkbox.setChecked(bool(self._config.ui_enter_to_send))
        else:
            self.ctrl_enter_checkbox.setChecked(True)
            self.enter_to_send_checkbox.setChecked(False)
        layout.addRow(self.ctrl_enter_checkbox)
        layout.addRow(self.enter_to_send_checkbox)
        
        # ボタン
        button_box = QDialogButtonBox()
        self._btn_save = button_box.addButton("保存", QDialogButtonBox.AcceptRole)
        self._btn_add = button_box.addButton("新規追加", QDialogButtonBox.ActionRole)
        self._btn_delete = button_box.addButton("削除", QDialogButtonBox.DestructiveRole)
        self._btn_cancel = button_box.addButton("キャンセル", QDialogButtonBox.RejectRole)
        self._btn_save.clicked.connect(self._on_save)
        self._btn_add.clicked.connect(self._on_add)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_cancel.clicked.connect(self.reject)
        layout.addRow(button_box)
    
    def _on_save(self):
        """既存または新規の内容で保存する。"""
        profile = self._profile_from_fields()
        ok, msg = validate_profile(profile)
        if not ok:
            QMessageBox.warning(self, "入力エラー", msg)
            return
        # 名前重複は上書き保存とみなす
        replaced = False
        for idx, p in enumerate(self._config.profiles):
            if p.name == profile.name:
                self._config.profiles[idx] = profile
                replaced = True
                break
        if not replaced:
            self._config.profiles.append(profile)
        self._config.current_profile_name = profile.name
        if self._finalize_config():
            self.accept()

    def _on_add(self):
        """新規追加（名前が未使用であることを前提）。"""
        profile = self._profile_from_fields()
        ok, msg = validate_profile(profile)
        if not ok:
            QMessageBox.warning(self, "入力エラー", msg)
            return
        if any(p.name == profile.name for p in self._config.profiles):
            QMessageBox.warning(self, "重複", "同名のプロファイルが既に存在します。別の名前を入力してください。")
            return
        self._config.profiles.append(profile)
        self._config.current_profile_name = profile.name
        if self._finalize_config():
            self.accept()

    def _on_delete(self):
        """現在名に一致するプロファイルを削除する。"""
        name = self.name_field.text().strip()
        if not name:
            return
        if len(self._config.profiles) <= 1:
            QMessageBox.information(self, "削除不可", "少なくとも1つのプロファイルが必要です。")
            return
        self._config.profiles = [p for p in self._config.profiles if p.name != name]
        # current の再設定
        self._config.current_profile_name = self._config.profiles[0].name
        if self._finalize_config():
            self.accept()
    
    def get_config(self) -> Config:
        """ダイアログの入力から Config を生成する。"""
        # タイムアウトとキーバインドはアプリ全体設定として反映
        api_key = self.api_key_field.text().strip()
        # タイムアウトは整数秒を ms に変換。無効入力は既定 30s を採用。
        try:
            read_timeout_s = max(1, int(self.timeout_field.text().strip()))
        except ValueError:
            read_timeout_s = 30
        # キーバインドは片方のみ有効にする（両方ONの場合は Ctrl+Enter 優先）
        ctrl_enter = self.ctrl_enter_checkbox.isChecked()
        enter_send = self.enter_to_send_checkbox.isChecked() and not ctrl_enter
        # 既存 profiles を使用（_finalize_config で更新済み）
        cfg = self._config
        cfg.request_timeout_ms = read_timeout_s * 1000
        cfg.ui_ctrl_enter_to_send = ctrl_enter
        cfg.ui_enter_to_send = enter_send
        return cfg

    # ---- helpers ----
    def _profile_from_fields(self) -> Profile:
        name = self.name_field.text().strip() or "default"
        ptype = self.type_field.currentText() or "openai"
        api_key = self.api_key_field.text().strip()
        return Profile(
            name=name,
            type=ptype,  # type: ignore[arg-type]
            base_url=self.base_url_field.text().strip(),
            model=self.model_field.text().strip(),
            api_key=api_key if api_key else None,
        )

    def _finalize_config(self) -> bool:
        """構成の最終バリデーション。重複名や必須項目を確認。"""
        # 一意性
        seen = set()
        for p in self._config.profiles:
            if p.name in seen:
                QMessageBox.warning(self, "入力エラー", f"プロファイル名が重複しています: {p.name}")
                return False
            seen.add(p.name)
            ok, msg = validate_profile(p)
            if not ok:
                QMessageBox.warning(self, "入力エラー", msg)
                return False
        if not self._config.current_profile_name:
            if self._config.profiles:
                self._config.current_profile_name = self._config.profiles[0].name
            else:
                QMessageBox.warning(self, "入力エラー", "少なくとも1つのプロファイルが必要です。")
                return False
        return True


class LoggingSettingsDialog(QDialog):
    """ログ/診断設定を編集するダイアログ。"""

    def __init__(self, parent=None, config: Optional[Config] = None):
        super().__init__(parent)
        self.setWindowTitle("ログ/診断設定")
        self.resize(360, 160)
        self._config = config or Config()

        layout = QFormLayout(self)

        # ログ有効/無効
        self.logging_enabled_checkbox = QCheckBox("ログを有効化（推奨）")
        self.logging_enabled_checkbox.setChecked(bool(getattr(self._config, "logging_enabled", True)))
        layout.addRow(self.logging_enabled_checkbox)

        # 詳細な環境情報の含有（診断用）
        self.env_details_checkbox = QCheckBox("診断情報に詳細な環境パスを含める")
        self.env_details_checkbox.setChecked(bool(getattr(self._config, "diagnostics_show_env_details", False)))
        layout.addRow(self.env_details_checkbox)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def _on_accept(self) -> None:
        self._config.logging_enabled = self.logging_enabled_checkbox.isChecked()
        self._config.diagnostics_show_env_details = self.env_details_checkbox.isChecked()
        self.accept()

    def get_config(self) -> Config:
        """更新済み Config を返す。"""
        return self._config

