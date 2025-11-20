"""
MainWindow と SettingsDialog を提供する GUI モジュール。
"""

from datetime import timezone
from typing import Optional, List
from pathlib import Path
import shutil
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QDialog,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QCheckBox,
    QFileDialog,
    QMessageBox,
    QComboBox,
    QLabel,
    QInputDialog,
    QTabWidget,
    QSpinBox,
    QDoubleSpinBox,
    QFontComboBox,
    QMenu,
    QSystemTrayIcon,
    QStyle,
)
from PySide6.QtCore import Qt, QObject, QThread, QUrl
from PySide6.QtGui import (
    QFont,
    QTextCursor,
    QDesktopServices,
    QGuiApplication,
    QShortcut,
    QKeySequence,
    QIcon,
)

from win_llm_chat_pyside.models import AttachmentMetadata, Message, PromptTemplate, RoleProfile, Session
from win_llm_chat_pyside.core.config import (
    Config,
    load_config,
    save_config,
    get_default_history_path,
    get_current_profile,
    Profile,
    validate_profile,
    get_sessions_dir,
    get_prompt_assets_dir,
    get_clipboard_image_dir,
)
from win_llm_chat_pyside.services.llm_client import OpenAiCompatibleClient
from win_llm_chat_pyside.services.workers import ChatWorker, StreamChatWorker
from win_llm_chat_pyside.services import storage
from win_llm_chat_pyside.core.factory import create_llm_client
from win_llm_chat_pyside.services.clipboard import ClipboardImageService
from win_llm_chat_pyside.core.app_logger import app_logger
from win_llm_chat_pyside.ui.dialogs.diagnostics_dialog import DiagnosticsInfoProvider
from win_llm_chat_pyside.features.sessions.session_repository import SessionRepository
from win_llm_chat_pyside.features.sessions.session_manager import SessionManager
from win_llm_chat_pyside.features.sessions.session_widgets import SessionListPanel
from win_llm_chat_pyside.features.attachments.attachment_context import AttachmentContextBuilder, AttachmentContextResult
from win_llm_chat_pyside.features.attachments.attachment_widgets import AttachmentListWidget
from win_llm_chat_pyside.features.attachments.attachments import AttachmentManager, FileTextExtractor
from win_llm_chat_pyside.features.attachments.attachment_prompts import AttachmentPromptService, PromptRequest
from win_llm_chat_pyside.features.prompts.prompt_repository import TemplateRepository, RoleProfileRepository
from win_llm_chat_pyside.features.prompts.prompt_template_store import PromptTemplateStore
from win_llm_chat_pyside.features.prompts.prompt_template_dialog import PromptTemplateManagerDialog
from win_llm_chat_pyside.features.prompts.prompt_utils import merge_template_text
from win_llm_chat_pyside.features.roles.role_profile_store import RoleProfileStore
from win_llm_chat_pyside.features.roles.role_profile_dialog import RoleProfileManagerDialog
from win_llm_chat_pyside.features.sessions.session_dialogs import SessionCreateDialog, RoleProfileSelectorDialog
from win_llm_chat_pyside.services.global_hotkey import GlobalHotkeyManager
from win_llm_chat_pyside.ui.window_controller import WindowController
from win_llm_chat_pyside.features.search.search_services import (
    SessionHit,
    SessionSearchService,
    AttachmentSearchService,
    AttachmentSearchInput,
)
from win_llm_chat_pyside.features.search.search_widgets import SessionSearchBar, AttachmentSearchPanel
from win_llm_chat_pyside.ui.dialogs.shortcut_help_dialog import ShortcutHelpDialog
from win_llm_chat_pyside.ui.shortcut_registry import ShortcutRegistry
from win_llm_chat_pyside.core.health_check import HealthChecker
from win_llm_chat_pyside.models.layout_mode import LayoutMode
from win_llm_chat_pyside.features.chat.layout_mode_state import LayoutModeState
from win_llm_chat_pyside.ui.main_layout import MainLayoutContainer
from win_llm_chat_pyside.features.chat.message_composer import MessageComposerWidget, PendingClipboardImage
from win_llm_chat_pyside.features.chat.chat_scroll_controller import ChatScrollController
from win_llm_chat_pyside.features.chat.chat_rich_text_view import ChatRichTextView
from win_llm_chat_pyside.features.chat.chat_search_highlighter import ChatSearchHighlighter
from win_llm_chat_pyside.features.chat.chat_streaming_updater import ChatStreamingUpdater
from win_llm_chat_pyside.ui.styles.theme import get_theme


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
        self._stop_button: Optional[QPushButton] = None
        self._profile_combo: Optional[QComboBox] = None
        self._template_combo: Optional[QComboBox] = None
        self._template_insert_button: Optional[QPushButton] = None
        self.session_panel: Optional[SessionListPanel] = None
        self.theme = get_theme()
        self.shortcut_registry = ShortcutRegistry()
        self._registered_global_hotkey: str | None = None
        self._streaming_active: bool = False
        self.chat_view: ChatRichTextView | None = None
        self.chat_streaming_updater: ChatStreamingUpdater | None = None
        self.chat_search_highlighter: ChatSearchHighlighter | None = None
        self.layout_mode_state = LayoutModeState(self.config)
        self.current_layout_mode: LayoutMode = self.layout_mode_state.mode

        assets_dir = get_prompt_assets_dir(self.config)
        self.template_repository = TemplateRepository(assets_dir)
        self.template_store = PromptTemplateStore(self.template_repository)
        self._templates_cache: List[PromptTemplate] = self.template_store.list_templates()
        self.role_profile_repository = RoleProfileRepository(assets_dir)
        self.role_profile_store = RoleProfileStore(self.role_profile_repository)
        self._role_profiles_cache: List[RoleProfile] = self.role_profile_store.list_profiles()
        sessions_dir = get_sessions_dir(self.config)
        self._legacy_history_file = self._legacy_history_path()
        self.session_repository = SessionRepository(sessions_dir)
        self.session_manager = SessionManager(
            repository=self.session_repository,
            legacy_path=self._legacy_history_file,
            persist=getattr(self.config, "history_enabled", True),
        )
        self.attachment_manager = AttachmentManager(
            session_manager=self.session_manager,
            text_extractor=FileTextExtractor(),
        )
        self.attachment_context_builder = AttachmentContextBuilder()
        self._clipboard_image_dir = get_clipboard_image_dir(self.config)
        self.clipboard_image_service = ClipboardImageService(
            max_bytes=int(getattr(self.config, "clipboard_image_max_bytes", 2_000_000) or 2_000_000),
            max_total_pixels=int(
                getattr(self.config, "clipboard_image_max_total_pixels", 8_000_000) or 8_000_000
            ),
        )
        self.attachment_prompt_service = AttachmentPromptService(
            template_store=self.template_store,
            role_profile_store=self.role_profile_store,
        )
        self.window_controller = WindowController(self)
        self.hotkey_manager = GlobalHotkeyManager(logger=app_logger)
        self.session_search_service = SessionSearchService()
        self.attachment_search_service = AttachmentSearchService()
        self.session_search_bar: SessionSearchBar | None = None
        self.attachment_search_panel: AttachmentSearchPanel | None = None
        self.main_tabs: QTabWidget | None = None
        self._has_attachments: bool = False
        self._session_search_keyword: str = ""
        self._session_search_hits: list[SessionHit] = []
        self._session_search_current_index: int = -1
        self._session_search_expected_hits: int = 0
        self._start_in_tray = bool(getattr(self.config, "start_minimized_to_tray", False))
        self._tray_icon: QSystemTrayIcon | None = None
        self._tray_menu: QMenu | None = None
        self._tray_toggle_action = None
        self._show_on_launch: bool = True
        self._initialize_client()
        self.attachment_widget: AttachmentListWidget | None = None
        self.current_layout_mode: LayoutMode = LayoutMode.from_value(
            getattr(self.config, "layout_mode", LayoutMode.FOCUSED.value)
        )
        
        # UI構築
        self._setup_ui()
        self._apply_chat_font_from_config()
        self._setup_menu()
        self._initialize_sessions()
        self._apply_global_hotkey_settings()
        self._apply_always_on_top()
        self._setup_shortcuts()
        self._setup_tray_icon()
        
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

    def _apply_chat_font_from_config(self) -> None:
        """Config のフォント設定をチャットビューに反映する。"""
        # 設定値がなければテーマ既定値でフォールバック
        family = getattr(self.config, "ui_markdown_font_family", "") or self.theme.typography.font_family
        size = int(getattr(self.config, "ui_markdown_font_size_pt", 0) or self.theme.typography.body_size)

        font: QFont = self.chat_view.font()
        font.setFamily(str(family))
        font.setPointSize(size)
        self.chat_view.setFont(font)
        
    def _setup_ui(self):
        """UI コンポーネントを配置する。"""
        self.session_panel = SessionListPanel(self)
        self.session_panel.create_requested.connect(self._on_session_create_requested)
        self.session_panel.rename_requested.connect(self._on_session_rename_requested)
        self.session_panel.delete_requested.connect(self._on_session_delete_requested)
        self.session_panel.session_selected.connect(self._on_session_selected)
        self.session_panel.search_requested.connect(self._on_session_list_search_requested)

        # プロファイル選択バー
        chat_column = QWidget()
        chat_layout = QVBoxLayout(chat_column)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(8)

        top_bar = QHBoxLayout()
        label = QLabel("プロファイル:")
        self._profile_combo = QComboBox()
        self._refresh_profile_combo()
        self._profile_combo.currentTextChanged.connect(self._on_profile_selected)
        top_bar.addWidget(label)
        top_bar.addWidget(self._profile_combo, stretch=1)
        chat_layout.addLayout(top_bar)

        self.session_search_bar = SessionSearchBar(self)
        self.session_search_bar.setVisible(False)
        self.session_search_bar.search_requested.connect(self._on_session_search_requested)
        self.session_search_bar.next_requested.connect(self._on_session_search_next)
        self.session_search_bar.previous_requested.connect(self._on_session_search_previous)
        self.session_search_bar.closed.connect(self._clear_session_search)
        chat_layout.addWidget(self.session_search_bar)
        
        # チャット表示（RichText ビュー）
        self.chat_view = ChatRichTextView(theme=self.theme)
        chat_layout.addWidget(self.chat_view, stretch=3)
        self.chat_streaming_updater = ChatStreamingUpdater(self.chat_view)
        self.chat_search_highlighter = ChatSearchHighlighter(self.chat_view)

        self.chat_scroll_controller = ChatScrollController(
            self.chat_view,
            auto_scroll_enabled=bool(getattr(self.config, "ui_autoscroll_enabled", True)),
        )

        self.message_composer = MessageComposerWidget(self, theme=self.theme)
        chat_layout.addWidget(self.message_composer)
        self.message_composer.send_requested.connect(self._on_send_clicked)
        self.message_composer.set_clipboard_image_service(self.clipboard_image_service)
        self.message_composer.clipboard_image_error.connect(self._on_clipboard_image_error)
        self.message_composer.clipboard_image_added.connect(self._on_clipboard_image_added)
        self._apply_send_shortcut_settings()

        self._template_combo = self.message_composer.template_combo
        self._template_insert_button = self.message_composer.template_insert_button
        self._template_insert_button.clicked.connect(self._on_template_insert_clicked)

        self.input_field = self.message_composer.input_field
        self.send_button = self.message_composer.send_button
        self.send_button.clicked.connect(self._on_send_clicked)
        self._stop_button = self.message_composer.stop_button
        self._stop_button.setEnabled(False)
        self._stop_button.clicked.connect(self._on_stop_clicked)

        self.attachment_widget = AttachmentListWidget(self)
        self.attachment_widget.attach_requested.connect(self._on_attachment_add)
        self.attachment_widget.summarize_requested.connect(self._on_attachment_summarize)
        self.attachment_widget.remove_requested.connect(self._on_attachment_remove)

        self.attachment_search_panel = AttachmentSearchPanel(self)
        self.attachment_search_panel.search_requested.connect(self._on_attachment_search_requested)
        self.attachment_search_panel.snippet_requested.connect(self._on_attachment_snippet_requested)

        attachments_column = QWidget()
        attachments_layout = QVBoxLayout(attachments_column)
        attachments_layout.setContentsMargins(0, 0, 0, 0)
        attachments_layout.setSpacing(8)
        attachments_layout.addWidget(self.attachment_widget, stretch=2)
        attachments_layout.addWidget(self.attachment_search_panel, stretch=1)

        self.main_tabs = QTabWidget(self)
        self.main_tabs.addTab(chat_column, "チャット")
        self.main_tabs.addTab(attachments_column, "添付")
        self.main_tabs.setTabToolTip(0, "チャット（Ctrl+1）")
        self.main_tabs.setTabToolTip(1, "添付（Ctrl+2）")

        initial_main_tab = getattr(self.config, "ui_main_selected_tab", "chat")
        if initial_main_tab == "attachments":
            self.main_tabs.setCurrentIndex(1)
        else:
            self.main_tabs.setCurrentIndex(0)
        self.main_tabs.currentChanged.connect(self._on_main_tab_changed)

        self.main_layout_container = MainLayoutContainer(
            self.session_panel,
            self.main_tabs,
            theme=self.theme,
        )
        self.setCentralWidget(self.main_layout_container)
        self._apply_layout_mode(self.current_layout_mode, persist_config=False, update_state=False)

        # ステータスバー（簡易インジケータ）
        self.statusBar().showMessage("")
        self._refresh_template_combo()
        
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

        template_action = settings_menu.addAction("プロンプトテンプレート...")
        template_action.triggered.connect(self._open_template_manager)

        role_profile_action = settings_menu.addAction("役割プロファイル...")
        role_profile_action.triggered.connect(self._open_role_profile_manager)

        change_role_profile_action = settings_menu.addAction("セッション役割プロファイルを変更...")
        change_role_profile_action.triggered.connect(self._on_change_session_role_profile)

        help_menu = menubar.addMenu("ヘルプ")
        shortcut_action = help_menu.addAction("ショートカットキー...")
        shortcut_action.setShortcut(QKeySequence("F1"))
        shortcut_action.triggered.connect(self._show_shortcut_help)
        self._register_shortcut_meta("F1", "ショートカットヘルプを開く", "ヘルプ")
        help_menu.addSeparator()
        logs_action = help_menu.addAction("ログフォルダを開く")
        logs_action.triggered.connect(self._open_logs_folder)
        diag_action = help_menu.addAction("診断情報...")
        diag_action.triggered.connect(self._show_diagnostics_dialog)

        view_menu = menubar.addMenu("表示")
        self.layout_mode_action = view_menu.addAction("コンパクトモード")
        self.layout_mode_action.setCheckable(True)
        self.layout_mode_action.triggered.connect(self._on_layout_mode_action_triggered)
        self._sync_layout_mode_action()

    def _initialize_sessions(self) -> None:
        """セッションを初期化し、必要に応じてヘルスチェックを実行する。"""
        # 起動時に簡易ヘルスチェックを実行
        try:
            checker = HealthChecker(self.config)
            result = checker.check_and_log()
            if not result.is_healthy:
                # 問題がある場合は警告を表示
                issues_text = "\n".join(f"  • {issue}" for issue in result.issues)
                warnings_text = "\n".join(f"  • {warning}" for warning in result.warnings)
                message = "アプリケーションの設定に問題が見つかりました:\n\n"
                if result.issues:
                    message += "【問題】\n" + issues_text + "\n\n"
                if result.warnings:
                    message += "【警告】\n" + warnings_text + "\n\n"
                message += "「ヘルプ > 診断情報...」で詳細を確認できます。"
                QMessageBox.warning(self, "ヘルスチェック", message)
        except Exception:
            # ヘルスチェック自体が失敗してもアプリは続行
            pass

        if not self.session_panel:
            return
        try:
            metas = self.session_manager.initialize()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "セッション", f"セッションの初期化に失敗しました。\n{exc}")
            self.session_panel.set_sessions([], None)
            return
        active_id = self.session_manager.get_active_session_id()
        self.session_panel.set_sessions(metas, active_id)
        if active_id:
            self._load_session_into_view(active_id, show_status=False)

    def _load_session_into_view(self, session_id: str, show_status: bool = True) -> None:
        try:
            session = self.session_manager.load_session(session_id)
            self.session_manager.set_active_session(session_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "セッション", f"セッションを読み込めませんでした。\n{exc}")
            return
        self.messages = [Message(role=m.role, content=m.content) for m in session.messages]
        self._update_chat_view()
        self._update_attachment_view(session)
        if show_status:
            self.statusBar().showMessage(f"セッション「{session.name}」を開きました", 3000)

    def _apply_global_hotkey_settings(self, show_dialog: bool = False) -> None:
        """Config に基づいてグローバルホットキー登録を更新する。"""
        if not getattr(self, "hotkey_manager", None) or not hasattr(self, "window_controller"):
            return
        enabled = bool(getattr(self.config, "global_hotkey_enabled", True))
        combination = getattr(self.config, "global_hotkey_combination", "Ctrl+Alt+Space") or "Ctrl+Alt+Space"
        success, error = self.hotkey_manager.apply_settings(
            enabled,
            combination,
            self._toggle_window_visibility,
        )
        if not success and enabled:
            message = error or "グローバルホットキーの登録に失敗しました。別の組み合わせを試してください。"
            self.statusBar().showMessage(message, 5000)
            if show_dialog:
                QMessageBox.warning(self, "グローバルホットキー", message)
            self._update_global_hotkey_registry(None)
        elif success and enabled:
            self.statusBar().showMessage(f"グローバルホットキー: {combination}", 3000)
            self._update_global_hotkey_registry(combination)
        else:
            self._update_global_hotkey_registry(None)
        self._update_tray_tooltip()

    def _apply_always_on_top(self, show_status: bool = False) -> None:
        """Config に基づいて常時最前面フラグを適用する。"""
        if not hasattr(self, "window_controller"):
            return
        enabled = bool(getattr(self.config, "always_on_top", False))
        self.window_controller.set_always_on_top(enabled)
        if show_status:
            message = "常に最前面を有効にしました" if enabled else "常に最前面を無効にしました"
            self.statusBar().showMessage(message, 3000)
        self._update_tray_tooltip()

    @property
    def should_show_on_launch(self) -> bool:
        """起動時にメインウィンドウを表示するかどうか。"""

        return bool(getattr(self, "_show_on_launch", True))

    def _toggle_window_visibility(self) -> None:
        """ホットキーやトレイから呼び出す表示トグル。"""

        if self.isVisible() and not self.isMinimized():
            self._hide_to_tray()
        else:
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        """ウィンドウを前面化し、トレイ状態を更新する。"""

        self.window_controller.show_and_focus()
        self._update_tray_menu_labels()
        self._update_tray_tooltip()

    def _hide_to_tray(self, initial: bool = False) -> None:
        """ウィンドウを隠し、必要に応じてトレイに退避する。"""

        if self._tray_icon:
            self.hide()
        else:
            self.window_controller.minimize_or_hide()
        if not initial:
            self.statusBar().showMessage("ウィンドウをトレイに移動しました", 3000)
        self._update_tray_menu_labels()
        self._update_tray_tooltip()

    def _setup_tray_icon(self) -> None:
        """トレイ起動フラグに基づいてトレイアイコンを初期化する。"""

        if not self._start_in_tray:
            return
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.statusBar().showMessage("システムトレイが利用できません。通常表示で起動します。", 5000)
            self._show_on_launch = True
            return
        icon = self._load_tray_icon()
        self._tray_icon = QSystemTrayIcon(icon, self)
        self._tray_menu = QMenu(self)
        self._tray_toggle_action = self._tray_menu.addAction("ウィンドウを表示")
        self._tray_toggle_action.triggered.connect(self._on_tray_toggle_action)
        quit_action = self._tray_menu.addAction("終了")
        quit_action.triggered.connect(self.close)
        self._tray_icon.setContextMenu(self._tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()
        self._show_on_launch = False
        self._hide_to_tray(initial=True)
        self._update_tray_menu_labels()
        self._update_tray_tooltip()

    def _on_tray_toggle_action(self) -> None:
        self._toggle_window_visibility()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._show_from_tray()

    def _update_tray_menu_labels(self) -> None:
        if not self._tray_toggle_action:
            return
        visible = self.isVisible() and not self.isMinimized()
        self._tray_toggle_action.setText("ウィンドウを隠す" if visible else "ウィンドウを表示")

    def _update_tray_tooltip(self) -> None:
        if not self._tray_icon:
            return
        visibility = "表示中" if self.isVisible() and not self.isMinimized() else "トレイ待機中"
        hotkey_enabled = bool(getattr(self.config, "global_hotkey_enabled", True))
        hotkey = getattr(self.config, "global_hotkey_combination", "Ctrl+Alt+Space") or "Ctrl+Alt+Space"
        hotkey_state = hotkey if hotkey_enabled else "無効"
        always_on_top = "オン" if getattr(self.config, "always_on_top", False) else "オフ"
        tooltip = (
            "LLM Chat Client\n"
            f"状態: {visibility}\n"
            f"ホットキー: {hotkey_state}\n"
            f"常に最前面: {always_on_top}"
        )
        self._tray_icon.setToolTip(tooltip)

    def _load_tray_icon(self) -> QIcon:
        icon_path = Path(__file__).resolve().parents[3] / "app.ico"
        if icon_path.exists():
            return QIcon(str(icon_path))
        if not self.windowIcon().isNull():
            return self.windowIcon()
        return self.style().standardIcon(QStyle.SP_DesktopIcon)

    def _switch_main_tab(self, name: str) -> None:
        """Switch between main 'チャット' and '添付' tabs."""

        if not self.main_tabs:
            return
        index = 0 if name == "chat" else 1
        if 0 <= index < self.main_tabs.count():
            self.main_tabs.setCurrentIndex(index)
            self._apply_main_tab_focus(name)

    def _on_main_tab_changed(self, index: int) -> None:
        """Persist main tab selection."""

        if not self.main_tabs:
            return
        name = "chat" if index == 0 else "attachments"
        self.config.ui_main_selected_tab = name
        save_config(self.config)
        self._apply_main_tab_focus(name)

    def _apply_main_tab_focus(self, name: str) -> None:
        """Apply reasonable focus target when main tab changes."""

        if name == "chat":
            composer = getattr(self, "message_composer", None)
            if composer is not None and getattr(composer, "input_field", None) is not None:
                composer.input_field.setFocus(Qt.ShortcutFocusReason)
        elif name == "attachments":
            if self._has_attachments and self.attachment_widget is not None:
                # 添付がある場合は一覧側にフォーカス
                self.attachment_widget.focus_preferred_item()
            elif self.attachment_search_panel is not None:
                # 添付がない場合は検索入力にフォーカス
                self.attachment_search_panel.focus_search_input()

    def _setup_shortcuts(self) -> None:
        """ショートカットキーを初期化する。"""
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._show_session_search_bar)
        self._register_shortcut_meta("Ctrl+F", "セッション内検索バーを表示", "検索")

        QShortcut(QKeySequence("Ctrl+Shift+F"), self, activated=self._focus_session_list_search)
        self._register_shortcut_meta("Ctrl+Shift+F", "セッション一覧検索にフォーカス", "検索")

        QShortcut(QKeySequence("Ctrl+Shift+M"), self, activated=self._toggle_layout_mode_shortcut)
        self._register_shortcut_meta("Ctrl+Shift+M", "集中／コンパクトモードを切り替え", "表示")

        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self._switch_main_tab("chat"))
        self._register_shortcut_meta("Ctrl+1", "チャットタブに切り替え", "表示")

        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self._switch_main_tab("attachments"))
        self._register_shortcut_meta("Ctrl+2", "添付タブに切り替え", "表示")

    def _register_shortcut_meta(self, key: str, description: str, category: str, scope: str = "app") -> None:
        """Register a shortcut description in the shared registry."""

        try:
            self.shortcut_registry.unregister(key)
        except ValueError:
            pass
        try:
            self.shortcut_registry.register(
                key=key,
                description=description,
                category=category,
                scope="global" if scope == "global" else "app",
            )
        except ValueError:
            # 同一説明で重複する場合は既存エントリを上書きする
            self.shortcut_registry.unregister(key)
            self.shortcut_registry.register(
                key=key,
                description=description,
                category=category,
                scope="global" if scope == "global" else "app",
            )

    def _update_global_hotkey_registry(self, combination: str | None) -> None:
        """Reflect the active global hotkey combination in the registry."""

        if self._registered_global_hotkey:
            self.shortcut_registry.unregister(self._registered_global_hotkey)
            self._registered_global_hotkey = None
        if combination:
            self.shortcut_registry.register(
                key=combination,
                description="ウィンドウを前面化／最小化",
                category="グローバルホットキー",
                scope="global",
            )
            self._registered_global_hotkey = combination

    def _apply_send_shortcut_settings(self) -> None:
        """Configure composer key bindings based on current config."""

        enter_to_send = bool(getattr(self.config, "ui_enter_to_send", False))
        ctrl_enter_to_send = bool(getattr(self.config, "ui_ctrl_enter_to_send", True))
        self.message_composer.configure_send_shortcuts(
            enter_to_send=enter_to_send,
            ctrl_enter_to_send=ctrl_enter_to_send,
        )
        if enter_to_send:
            self._register_shortcut_meta("Enter", "メッセージを送信", "チャット")
        else:
            self.shortcut_registry.unregister("Enter")
        if ctrl_enter_to_send:
            self._register_shortcut_meta("Ctrl+Enter", "メッセージを送信", "チャット")
        else:
            self.shortcut_registry.unregister("Ctrl+Enter")

    def _on_clipboard_image_error(self, message: str) -> None:
        self.statusBar().showMessage(message, 5000)

    def _on_clipboard_image_added(self, size_bytes: int) -> None:
        kb = max(1, size_bytes // 1024)
        self.statusBar().showMessage(f"画像を貼り付けました（約 {kb} KB）", 4000)

    def _on_layout_mode_action_triggered(self, checked: bool) -> None:
        mode = LayoutMode.COMPACT if checked else LayoutMode.FOCUSED
        self._apply_layout_mode(mode, persist_config=True, update_state=True, show_status=True)

    def _toggle_layout_mode_shortcut(self) -> None:
        new_mode = self.layout_mode_state.toggle()
        self._apply_layout_mode(new_mode, persist_config=True, update_state=False, show_status=True)

    def _sync_layout_mode_action(self) -> None:
        action = getattr(self, "layout_mode_action", None)
        if action is None:
            return
        action.blockSignals(True)
        action.setChecked(self.current_layout_mode is LayoutMode.COMPACT)
        action.blockSignals(False)

    def _apply_layout_mode(
        self,
        mode: LayoutMode,
        *,
        persist_config: bool,
        update_state: bool,
        show_status: bool = False,
    ) -> None:
        self.current_layout_mode = mode
        if getattr(self, "main_layout_container", None):
            self.main_layout_container.set_layout_mode(mode)
        if getattr(self, "message_composer", None):
            self.message_composer.set_layout_mode(mode)
        self._sync_layout_mode_action()
        if update_state:
            self.layout_mode_state.set_mode(mode)
        if persist_config:
            save_config(self.config)
        if show_status:
            label = "コンパクトモード" if mode is LayoutMode.COMPACT else "集中モード"
            self.statusBar().showMessage(f"{label}に切り替えました", 3000)

    def _on_session_create_requested(self) -> None:
        dialog = SessionCreateDialog(self._role_profiles_cache, self)
        if dialog.exec() != QDialog.Accepted:
            return
        name, profile_id = dialog.get_values()
        prompt = self._get_profile_prompt(profile_id)
        try:
            session = self.session_manager.create_session(name or None, profile_id, prompt)
        except Exception as exc:  # noqa: BLE001
            self._log_and_show_error(
                "セッション",
                "セッションの作成に失敗しました。",
                exc,
                "session.create_failed",
            )
            return
        metas = self.session_manager.list_sessions()
        if self.session_panel:
            self.session_panel.set_sessions(metas, session.id)
        self._load_session_into_view(session.id)

    def _on_session_rename_requested(self, session_id: str) -> None:
        metas = {meta.id: meta for meta in self.session_manager.list_sessions()}
        current_name = metas.get(session_id).name if session_id in metas else ""
        new_name, ok = QInputDialog.getText(self, "セッション名の変更", "新しいセッション名:", text=current_name)
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name:
            QMessageBox.warning(self, "セッション", "セッション名を入力してください。")
            return
        self.session_manager.rename_session(session_id, new_name)
        active_id = self.session_manager.get_active_session_id()
        if self.session_panel:
            self.session_panel.set_sessions(self.session_manager.list_sessions(), active_id)
        self.statusBar().showMessage(f"セッション名を「{new_name}」に変更しました", 3000)

    def _on_session_delete_requested(self, session_id: str) -> None:
        if len(self.session_manager.list_sessions()) <= 1:
            QMessageBox.information(self, "セッション", "最後のセッションは削除できません。")
            return
        confirm = QMessageBox.question(self, "セッション削除", "選択したセッションを削除しますか？")
        if confirm != QMessageBox.Yes:
            return
        try:
            new_active = self.session_manager.delete_session(session_id)
        except ValueError as exc:
            QMessageBox.warning(self, "セッション", str(exc))
            return
        self._cleanup_session_clipboard_dir(session_id)
        active_id = new_active or (self.session_manager.list_sessions()[0].id if self.session_manager.list_sessions() else None)
        if self.session_panel:
            self.session_panel.set_sessions(self.session_manager.list_sessions(), active_id)
        if active_id:
            self._load_session_into_view(active_id)
        else:
            self.messages = []
            self._update_chat_view()

    def _cleanup_session_clipboard_dir(self, session_id: str) -> None:
        base = getattr(self, "_clipboard_image_dir", None)
        if not base:
            return
        target = base / session_id
        try:
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
        except Exception:
            # クリーンアップ失敗は致命ではないので握りつぶす
            pass

    def _on_session_selected(self, session_id: str) -> None:
        current_id = self.session_manager.get_active_session_id()
        if session_id == current_id:
            return
        if self._sending:
            QMessageBox.information(self, "セッション", "送信中はセッションを切り替えられません。")
            if self.session_panel and current_id:
                self.session_panel.set_active_session(current_id)
            return
        self._persist_active_session()
        self._load_session_into_view(session_id)

    def _show_session_search_bar(self) -> None:
        if self.session_search_bar:
            self.session_search_bar.show_bar()

    def _focus_session_list_search(self) -> None:
        if self.session_panel:
            self.session_panel.focus_search()

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
        self._refresh_template_combo()

    def _refresh_template_combo(self) -> None:
        if not self._template_combo:
            return
        has_templates = bool(self._templates_cache)
        self._template_combo.blockSignals(True)
        self._template_combo.clear()
        for template in self._templates_cache:
            self._template_combo.addItem(template.title, template.id)
        self._template_combo.blockSignals(False)
        self._template_combo.setEnabled(has_templates)
        if self._template_insert_button:
            self._template_insert_button.setEnabled(has_templates)

    def _on_template_insert_clicked(self) -> None:
        if not self._template_combo or not self.input_field:
            return
        template_id = self._template_combo.currentData()
        if not template_id:
            QMessageBox.information(self, "テンプレート", "挿入するテンプレートを選択してください。")
            return
        template = next((tpl for tpl in self._templates_cache if tpl.id == template_id), None)
        if not template:
            QMessageBox.warning(self, "テンプレート", "選択したテンプレートが見つかりません。")
            return
        merged = merge_template_text(self.input_field.toPlainText(), template.body)
        self.input_field.setPlainText(merged)
        cursor = self.input_field.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.input_field.setTextCursor(cursor)
        self.input_field.setFocus()

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

        session_id = self.session_manager.get_active_session_id()
        if not session_id:
            QMessageBox.information(self, "送信", "アクティブなセッションがありません。")
            return
        try:
            self._persist_pending_clipboard_images(session_id)
        except Exception as exc:  # noqa: BLE001
            self._log_and_show_error(
                "送信",
                "画像添付の保存に失敗しました。",
                exc,
                "clipboard.attach_failed",
            )
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
        
        selected_attachment_ids: list[str] = []
        if self.attachment_widget:
            selected_attachment_ids = self.attachment_widget.selected_attachment_ids()

        attachment_context_result: AttachmentContextResult | None = None
        session_for_attachments: Session | None = None
        included_filenames: list[str] = []
        if selected_attachment_ids:
            session_for_attachments = self._get_active_session_for_attachment()
            if not session_for_attachments:
                return
            attachment_context_result = self.attachment_context_builder.build(
                session_for_attachments,
                selected_attachment_ids,
                max_chars=int(getattr(self.config, "attachment_send_max_chars", 20_000) or 0),
            )
            name_map = {attachment.id: attachment.filename for attachment in session_for_attachments.attachments}
            included_filenames = [
                name_map.get(att_id, att_id) for att_id in attachment_context_result.included_ids
            ]
            self._handle_attachment_context_outcome(session_for_attachments, attachment_context_result)

        # 送信中は UI を無効化＋インジケータ表示
        self._set_busy(True)
        
        # ユーザーメッセージを追加
        attachment_context_text = attachment_context_result.text if attachment_context_result else ""
        user_payload = self._compose_user_message(user_input, included_filenames, attachment_context_text)
        user_message = Message(role="user", content=user_payload)
        self.messages.append(user_message)

        # ビュー更新（ユーザーメッセージ）＋自動スクロール
        self._update_chat_view()
        self.chat_scroll_controller.scroll_to_end(force=True)

        # アシスタント空メッセージを先行追加（逐次追記の受け皿）
        assistant_placeholder = Message(role="assistant", content="")
        self.messages.append(assistant_placeholder)
        self._update_chat_view()
        self.chat_scroll_controller.scroll_to_end(force=True)

        # ストリーミング Worker 起動
        self._start_stream_worker()

    def _persist_pending_clipboard_images(self, session_id: str) -> None:
        pending = self.message_composer.pending_clipboard_images()
        if not pending:
            return
        saved = 0
        for image in pending:
            path = self._write_clipboard_image_file(session_id, image)
            self.attachment_manager.add_attachment(
                session_id,
                path,
                source="clipboard_image",
                stored_file_path=str(path),
                skip_text_extraction=True,
            )
            saved += 1
        self.message_composer.clear_clipboard_images()
        self._load_session_into_view(session_id, show_status=False)
        self.statusBar().showMessage(f"{saved}件の画像を添付しました", 4000)

    def _write_clipboard_image_file(self, session_id: str, image: PendingClipboardImage) -> Path:
        target_dir = self._clipboard_image_dir / session_id
        target_dir.mkdir(parents=True, exist_ok=True)
        timestamp = image.captured_at.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"{session_id[:8]}-clip-{timestamp}-{image.id[:6]}.png"
        path = target_dir / filename
        with open(path, "wb") as fp:
            fp.write(image.data)
        return path
    
    def _update_chat_view(self):
        """メッセージリストから表示用データを生成してビューを更新する。"""
        if not self.chat_view:
            return
        display_messages: list[Message] = []
        for msg in self.messages:
            display_messages.append(
                Message(role=msg.role, content=self._display_message_content(msg))
            )
        self.chat_view.set_messages(display_messages)
        self._reapply_session_search_highlight()

    def _update_attachment_view(self, session: Session) -> None:
        if not self.attachment_widget:
            return
        self.attachment_widget.clear_send_selection()
        self.attachment_widget.set_attachments(session.attachments)
        has_attachments = bool(session.attachments)
        self._has_attachments = has_attachments
        if self.attachment_search_panel:
            self.attachment_search_panel.set_attachments_available(has_attachments)
            if not has_attachments:
                self.attachment_search_panel.update_results("", [])

    # ---- search handling ----
    def _on_session_search_requested(self, keyword: str) -> None:
        normalized = self.session_search_service.normalize_keyword(keyword)
        self._session_search_keyword = normalized
        if not self.session_search_service.is_valid_keyword(normalized):
            self._session_search_hits = []
            self._session_search_current_index = -1
            if self.chat_search_highlighter:
                self.chat_search_highlighter.clear()
            if self.session_search_bar:
                self.session_search_bar.update_status(current=0, total=0)
            if normalized:
                self.statusBar().showMessage("検索キーワードは2文字以上で入力してください。", 4000)
            return
        hits = self.session_search_service.search_in_session(self.messages, normalized)
        self._session_search_hits = hits
        self._session_search_expected_hits = len(hits)
        self._apply_session_search_highlight()
        if hits:
            self.statusBar().showMessage(f"セッション内検索: {len(hits)}件ヒット", 2000)
        else:
            self.statusBar().showMessage("セッション内検索: 一致なし", 2000)

    def _on_session_search_next(self) -> None:
        if not self._session_search_hits:
            return
        self._session_search_current_index = (self._session_search_current_index + 1) % len(self._session_search_hits)
        self._focus_session_search_hit()

    def _on_session_search_previous(self) -> None:
        if not self._session_search_hits:
            return
        self._session_search_current_index = (self._session_search_current_index - 1) % len(self._session_search_hits)
        self._focus_session_search_hit()

    def _apply_session_search_highlight(self) -> None:
        if self.chat_search_highlighter:
            self.chat_search_highlighter.apply_hits(self._session_search_hits)
        if not self._session_search_hits:
            self._session_search_current_index = -1
        elif self._session_search_current_index == -1 or self._session_search_current_index >= len(self._session_search_hits):
            self._session_search_current_index = 0
            self._focus_session_search_hit()
        if self.session_search_bar:
            current = self._session_search_current_index + 1 if self._session_search_hits else 0
            self.session_search_bar.update_status(current=current, total=len(self._session_search_hits))

    def _focus_session_search_hit(self) -> None:
        if not self._session_search_hits:
            return
        # hit = self._session_search_hits[self._session_search_current_index]
        if self.chat_search_highlighter:
            self.chat_search_highlighter.focus_hit(self._session_search_current_index)
        if self.session_search_bar:
            self.session_search_bar.update_status(
                current=self._session_search_current_index + 1,
                total=len(self._session_search_hits),
            )

    def _reapply_session_search_highlight(self) -> None:
        if self._session_search_keyword:
            self._apply_session_search_highlight()

    def _clear_session_search(self) -> None:
        self._session_search_keyword = ""
        self._session_search_hits = []
        self._session_search_current_index = -1
        if self.chat_search_highlighter:
            self.chat_search_highlighter.clear()
        if self.session_search_bar:
            self.session_search_bar.update_status(current=0, total=0)

    def _on_session_list_search_requested(self, keyword: str) -> None:
        if not self.session_panel:
            return
        normalized = self.session_search_service.normalize_keyword(keyword)
        if not normalized:
            self.session_panel.apply_filter(None)
            self.statusBar().showMessage("セッション検索をクリアしました。", 3000)
            return
        if not self.session_search_service.is_valid_keyword(normalized):
            self.statusBar().showMessage("セッション検索は2文字以上で入力してください。", 4000)
            return
        summaries = self.session_manager.build_session_summaries()
        matched_ids = self.session_search_service.search_in_summaries(summaries, normalized)
        self.session_panel.apply_filter(set(matched_ids))
        self.statusBar().showMessage(f"セッション検索: {len(matched_ids)}件ヒット", 3000)

    def _on_attachment_search_requested(self, keyword: str) -> None:
        if not self.attachment_search_panel:
            return
        normalized = self.attachment_search_service.normalize_keyword(keyword)
        if not self.attachment_search_service.is_valid_keyword(normalized):
            self.statusBar().showMessage("添付テキスト検索は2文字以上で入力してください。", 4000)
            self.attachment_search_panel.update_results("", [])
            return
        session = self._get_active_session_for_attachment()
        if not session:
            return
        inputs = self._collect_attachment_search_inputs(session)
        if not inputs:
            QMessageBox.information(self, "添付検索", "検索対象となる抽出済みテキストがありません。")
            return
        hits = self.attachment_search_service.search_in_attachments(inputs, normalized)
        self.attachment_search_panel.update_results(normalized, hits)
        self.statusBar().showMessage(f"添付検索: {len(hits)}件ヒット", 3000)

    def _on_attachment_snippet_requested(self, attachment_id: str, snippet: str) -> None:
        session = self._get_active_session_for_attachment()
        if not session:
            return
        metadata = self._find_attachment(session, attachment_id)
        if not metadata:
            QMessageBox.warning(self, "添付検索", "選択した添付ファイルが見つかりませんでした。")
            return
        keyword = ""
        if self.attachment_search_panel:
            keyword = self.attachment_search_panel.current_keyword
        snippet_text = snippet.strip()
        payload_lines = [
            "[添付テキスト検索抜粋]",
            f"ファイル: {metadata.filename}",
        ]
        if keyword:
            payload_lines.append(f"検索キーワード: {keyword}")
        payload_lines.append("")
        payload_lines.append(snippet_text)
        payload = "\n".join(payload_lines).strip()
        existing = self.input_field.toPlainText().strip()
        if existing:
            payload = f"{existing}\n\n{payload}"
        self.input_field.setPlainText(payload)
        self.input_field.moveCursor(QTextCursor.End)
        self.statusBar().showMessage("抜粋を入力欄に挿入しました。必要に応じて送信してください。", 5000)

    def _collect_attachment_search_inputs(self, session: Session) -> list[AttachmentSearchInput]:
        inputs: list[AttachmentSearchInput] = []
        for metadata in session.attachments:
            text = session.attachment_texts.get(metadata.id)
            if not text:
                continue
            inputs.append(
                AttachmentSearchInput(
                    attachment_id=metadata.id,
                    filename=metadata.filename,
                    text=text,
                )
            )
        return inputs
    
    # ---- attachment handling ----
    def _on_attachment_add(self) -> None:
        session_id = self.session_manager.get_active_session_id()
        if not session_id:
            QMessageBox.information(self, "添付ファイル", "アクティブなセッションがありません。")
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "ファイルを選択")
        if not file_path:
            return
        try:
            metadata = self.attachment_manager.add_attachment(session_id, Path(file_path))
        except Exception as exc:  # noqa: BLE001
            self._log_and_show_error(
                "添付ファイル",
                "ファイルの添付に失敗しました。",
                exc,
                "attachment.add_failed",
            )
            return
        self._load_session_into_view(session_id, show_status=False)
        self.statusBar().showMessage(f"「{metadata.filename}」を添付しました", 3000)

    def _on_attachment_remove(self, attachment_id: str) -> None:
        session_id = self.session_manager.get_active_session_id()
        if not session_id:
            QMessageBox.information(self, "添付ファイル", "アクティブなセッションがありません。")
            return
        confirm = QMessageBox.question(
            self,
            "添付ファイル削除",
            "選択した添付ファイルを削除しますか？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self.attachment_manager.remove_attachment(session_id, attachment_id)
        except Exception as exc:  # noqa: BLE001
            self._log_and_show_error(
                "添付ファイル",
                "添付ファイルの削除に失敗しました。",
                exc,
                "attachment.remove_failed",
            )
            return
        self._load_session_into_view(session_id, show_status=False)
        self.statusBar().showMessage("添付ファイルを削除しました", 3000)

    def _on_attachment_summarize(self, attachment_id: str) -> None:
        session = self._get_active_session_for_attachment()
        if not session:
            return
        metadata = self._find_attachment(session, attachment_id)
        if not metadata:
            QMessageBox.warning(self, "添付ファイル", "選択した添付ファイルが見つかりません。")
            return
        if metadata.status != "ready":
            QMessageBox.information(self, "添付ファイル", "テキスト抽出が完了していません。しばらく待ってから再度お試しください。")
            return
        text = session.attachment_texts.get(attachment_id, "")
        if not text:
            QMessageBox.warning(self, "添付ファイル", "抽出済みテキストが見つかりませんでした。もう一度添付してください。")
            return
        prompt_request = self.attachment_prompt_service.build_summary_request(session, metadata, text)
        display_user_content = f"[ファイル要約] {metadata.filename}"
        self._send_attachment_prompt(prompt_request, display_user_content)

    def _get_active_session_for_attachment(self) -> Session | None:
        session_id = self.session_manager.get_active_session_id()
        if not session_id:
            QMessageBox.information(self, "添付ファイル", "アクティブなセッションがありません。")
            return None
        try:
            return self.session_manager.load_session(session_id)
        except Exception as exc:  # noqa: BLE001
            self._log_and_show_error(
                "添付ファイル",
                "セッションの読み込みに失敗しました。",
                exc,
                "attachment.session_load_failed",
            )
            return None

    def _find_attachment(self, session: Session, attachment_id: str) -> AttachmentMetadata | None:
        for attachment in session.attachments:
            if attachment.id == attachment_id:
                return attachment
        return None

    def _send_attachment_prompt(self, prompt_request: PromptRequest, display_user_content: str) -> None:
        if not self.llm_client:
            QMessageBox.warning(self, "送信", "LLM クライアントが設定されていません。")
            return
        if self._sending:
            QMessageBox.information(self, "送信", "送信中は操作できません。")
            return
        self._set_busy(True)
        self.messages.append(Message(role="user", content=display_user_content))
        self.messages.append(Message(role="assistant", content=""))
        self._update_chat_view()
        self.chat_scroll_controller.scroll_to_end(force=True)
        llm_options = {
            "temperature": prompt_request.temperature,
            "top_p": prompt_request.top_p,
        }
        self._start_stream_worker(messages_override=prompt_request.messages, llm_options=llm_options)

    def _compose_user_message(
        self,
        user_text: str,
        attachment_names: list[str],
        attachment_context: str,
    ) -> str:
        """LLM に渡すユーザーメッセージ本文を構築する。

        - チャットペインでは本文＋添付ファイル名のみを表示する
        - 実際の LLM には添付テキストコンテキストも含めて送信する
        """

        parts: list[str] = []
        user_text = user_text.strip()
        attachment_context = attachment_context.strip()

        if user_text:
            parts.append(user_text)
        if attachment_names:
            names = ", ".join(attachment_names)
            parts.append(f"[添付ファイル]\n{names}")
        if attachment_context:
            parts.append(f"[添付コンテキスト]\n{attachment_context}")
        return "\n\n".join(parts) if parts else user_text

    def _display_message_content(self, message: Message) -> str:
        if message.role == "user":
            return self._visible_user_content(message.content)
        return message.content

    def _visible_user_content(self, full_content: str) -> str:
        """チャットペインに表示するユーザーコンテンツ部分を抽出する。

        添付コンテキスト本体（[添付コンテキスト] 以降）は表示せず、
        本文と添付ファイル名のみを表示する。
        """

        marker = "[添付コンテキスト]"
        if marker not in full_content:
            return full_content
        before, _, _ = full_content.partition(marker)
        return before.rstrip()

    def _handle_attachment_context_outcome(
        self,
        session: Session,
        result: AttachmentContextResult,
    ) -> None:
        name_map = {attachment.id: attachment.filename for attachment in session.attachments}
        notices: list[str] = []
        if result.included_ids:
            included_names = ", ".join(name_map.get(att_id, att_id) for att_id in result.included_ids)
            notices.append(f"添付付き送信: {len(result.included_ids)}件 ({included_names})")
        if result.skipped_ids:
            skipped_names = ", ".join(name_map.get(att_id, att_id) for att_id in result.skipped_ids)
            notices.append(f"抽出済みテキストが見つからず送信できなかった添付: {skipped_names}")
        if result.truncated and getattr(self.config, "attachment_send_truncate_notice_enabled", True):
            notices.append("添付テキストが長いため一部を省略して送信しました")
        if notices:
            self.statusBar().showMessage(" / ".join(notices), 6000)

        try:
            app_logger.info(
                "chat.send.attachments",
                {
                    "included_count": len(result.included_ids),
                    "skipped_count": len(result.skipped_ids),
                    "total_chars": result.total_chars,
                    "truncated": result.truncated,
                },
            )
        except Exception:
            pass


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
            self._apply_global_hotkey_settings(show_dialog=True)
            self._apply_always_on_top(show_status=True)
            self._apply_send_shortcut_settings()
            self.chat_scroll_controller.set_auto_scroll_enabled(
                bool(getattr(self.config, "ui_autoscroll_enabled", True))
            )

            # チャットビューのフォント設定を即時反映
            self._apply_chat_font_from_config()

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

    def _open_template_manager(self) -> None:
        """プロンプトテンプレート管理ダイアログを開く。"""
        dialog = PromptTemplateManagerDialog(self.template_store, self)
        dialog.exec()
        self._templates_cache = self.template_store.list_templates()
        self._refresh_template_combo()

    def _open_role_profile_manager(self) -> None:
        """役割プロファイル管理ダイアログを開く。"""
        dialog = RoleProfileManagerDialog(self.role_profile_store, self)
        dialog.exec()
        self._refresh_role_profiles_cache()
        self.statusBar().showMessage("役割プロファイルを更新しました", 3000)

    def _refresh_role_profiles_cache(self) -> None:
        self._role_profiles_cache = self.role_profile_store.list_profiles()

    def _get_profile_prompt(self, profile_id: Optional[str]) -> Optional[str]:
        if not profile_id:
            return None
        profile = next((p for p in self._role_profiles_cache if p.id == profile_id), None)
        return profile.system_prompt if profile else None

    def _log_and_show_error(self, title: str, message: str, exc: Exception, event: str) -> None:
        try:
            app_logger.error(event, {"error": str(exc)})
        except Exception:
            pass
        QMessageBox.critical(self, title, f"{message}\n{exc}")

    def _on_change_session_role_profile(self) -> None:
        active_id = self.session_manager.get_active_session_id()
        if not active_id:
            QMessageBox.information(self, "役割プロファイル", "アクティブなセッションがありません。")
            return
        try:
            session = self.session_manager.load_session(active_id)
        except Exception as exc:  # noqa: BLE001
            self._log_and_show_error(
                "役割プロファイル",
                "セッションの読み込みに失敗しました。",
                exc,
                "session.load_for_role_profile_failed",
            )
            return
        dialog = RoleProfileSelectorDialog(self._role_profiles_cache, session.role_profile_id, self)
        if dialog.exec() != QDialog.Accepted:
            return
        selected_id = dialog.get_selected_profile_id()
        selected_prompt = self._get_profile_prompt(selected_id)
        if selected_id == session.role_profile_id:
            return
        confirm = QMessageBox.question(
            self,
            "役割プロファイルの変更",
            "役割プロファイルを変更すると、以降の応答の傾向が変化します。\n続行しますか？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self.session_manager.apply_role_profile(active_id, selected_id, selected_prompt)
        except Exception as exc:  # noqa: BLE001
            self._log_and_show_error(
                "役割プロファイル",
                "役割プロファイルの更新に失敗しました。",
                exc,
                "session.apply_role_profile_failed",
            )
            return
        if self.session_panel:
            self.session_panel.set_sessions(self.session_manager.list_sessions(), active_id)
        self._load_session_into_view(active_id)
        self.statusBar().showMessage("役割プロファイルを更新しました", 3000)

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
            self._streaming_active = False
            if self.chat_streaming_updater:
                self.chat_streaming_updater.finalize()
            self._set_busy(False)
            # UI 再有効化後にフォーカスを入力欄へ戻す
            self.message_composer.focus_input_field()

    # Streaming 用
    def _start_stream_worker(
        self,
        messages_override: Optional[list[Message]] = None,
        llm_options: Optional[dict] = None,
    ):
        """バックグラウンドでストリーミング送信を開始する。"""
        messages_snapshot = list(messages_override) if messages_override is not None else list(self.messages)
        self._streaming_active = True
        self._worker_thread = QThread(self)
        worker = StreamChatWorker(self.llm_client, messages_snapshot, llm_options=llm_options)  # type: ignore[arg-type]
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
        display_text = self._display_message_content(self.messages[-1])
        if self.chat_streaming_updater and self.chat_view:
            last_index = len(self.messages) - 1
            if self.chat_scroll_controller:
                self.chat_scroll_controller.suspend_user_tracking()
            try:
                if self.chat_streaming_updater.active_index != last_index:
                    self.chat_streaming_updater.begin(message_index=last_index)
                self.chat_streaming_updater.update_text(display_text)
            finally:
                if self.chat_scroll_controller:
                    self.chat_scroll_controller.resume_user_tracking()
        else:
            self._update_chat_view()
        if self.config.ui_autoscroll_enabled and self.chat_scroll_controller and not self.chat_scroll_controller.is_user_override:
            self.chat_scroll_controller.scroll_to_end()

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
        if self.chat_streaming_updater:
            self.chat_streaming_updater.finalize()
        self._update_chat_view()
        if self.config.ui_autoscroll_enabled:
            self.chat_scroll_controller.scroll_to_end(force=True)
        self.input_field.clear()
        self._persist_active_session()

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
            self.chat_scroll_controller.scroll_to_end()
        self.input_field.clear()
        self._persist_active_session()

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
        self._persist_active_session()

    def _check_history_limits(self) -> None:
        """履歴のソフト上限を超えた場合に非ブロッキングで通知する。"""
        max_msgs = int(getattr(self.config, "history_max_messages", 400) or 400)
        max_chars = int(getattr(self.config, "history_max_chars", 200000) or 200000)
        num_msgs, total_chars = storage.calculate_history_size(self.messages)
        if num_msgs > max_msgs or total_chars > max_chars:
            self.statusBar().showMessage("履歴が大きくなっています。保存/エクスポート前に見直しを検討してください。", 5000)

    def _persist_active_session(self) -> None:
        if not getattr(self.config, "history_enabled", True):
            return
        active_id = self.session_manager.get_active_session_id()
        if not active_id:
            return
        try:
            self.session_manager.save_session_messages(active_id, self.messages)
        except Exception:
            QMessageBox.warning(self, "セッション", "セッションの保存に失敗しました。")

    def _legacy_history_path(self) -> Path:
        cfg_path = getattr(self.config, "history_path", None)
        if cfg_path:
            return Path(cfg_path)
        return get_default_history_path()

    def closeEvent(self, event):  # noqa: N802 - Qt 既定名
        """ウィンドウクローズ時にアクティブセッションを保存する。"""
        try:
            if getattr(self.config, "history_enabled", True):
                self._check_history_limits()
                self._persist_active_session()
        except Exception:
            QMessageBox.warning(self, "保存エラー", "セッションの保存に失敗しました。")
        finally:
            try:
                app_logger.info("app.exit", {"profile_name": self.config.current_profile_name or ""})
            except Exception:
                pass
            try:
                if getattr(self, "hotkey_manager", None):
                    self.hotkey_manager.shutdown()
            except Exception:
                pass
            try:
                if getattr(self, "_tray_icon", None):
                    self._tray_icon.hide()
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

    def _show_shortcut_help(self) -> None:
        """ショートカットキーヘルプダイアログを表示する。"""
        dialog = ShortcutHelpDialog(self.shortcut_registry, self)
        dialog.exec()

    def _show_diagnostics_dialog(self) -> None:
        """診断情報ダイアログを表示する。"""
        provider = DiagnosticsInfoProvider(self.config)
        info = provider.collect()
        text = provider.format_text(info)

        # ヘルスチェック結果を追加
        try:
            checker = HealthChecker(self.config)
            health_result = checker.check()
            text += "\n\n=== ヘルスチェック結果 ===\n"
            if health_result.is_healthy:
                text += "状態: 正常\n"
            else:
                text += "状態: 問題あり\n"
            if health_result.issues:
                text += "\n【問題】\n"
                for issue in health_result.issues:
                    text += f"  • {issue}\n"
            if health_result.warnings:
                text += "\n【警告】\n"
                for warning in health_result.warnings:
                    text += f"  • {warning}\n"
        except Exception:
            text += "\n\n=== ヘルスチェック結果 ===\n"
            text += "状態: チェック失敗\n"

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
    """アプリ全体の設定を編集するダイアログ。"""
    
    def __init__(self, parent=None, config: Optional[Config] = None):
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.resize(640, 420)
        self._config = config or Config()

        main_layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        main_layout.addWidget(self._tabs)

        # ---- タブ: 接続・プロファイル ----
        self._init_profile_tab()

        # ---- タブ: チャット・挙動 ----
        self._init_behavior_tab()

        # ---- タブ: 履歴・セッション ----
        self._init_history_tab()

        # ---- タブ: 表示・フォント ----
        self._init_display_tab()

        # ---- タブ: ネットワーク ----
        self._init_network_tab()

        # ボタン（共通フッター）
        button_box = QDialogButtonBox()
        self._btn_save = button_box.addButton("保存", QDialogButtonBox.AcceptRole)
        self._btn_add = button_box.addButton("新規追加", QDialogButtonBox.ActionRole)
        self._btn_delete = button_box.addButton("削除", QDialogButtonBox.DestructiveRole)
        self._btn_cancel = button_box.addButton("キャンセル", QDialogButtonBox.RejectRole)
        self._btn_save.clicked.connect(self._on_save)
        self._btn_add.clicked.connect(self._on_add)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_cancel.clicked.connect(self.reject)
        main_layout.addWidget(button_box)

    # ---- タブ初期化 ----
    def _init_profile_tab(self) -> None:
        tab = QWidget()
        layout = QFormLayout(tab)

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

        self._tabs.addTab(tab, "接続・プロファイル")

    def _init_behavior_tab(self) -> None:
        tab = QWidget()
        layout = QFormLayout(tab)

        # 送信キーバインド
        self.ctrl_enter_checkbox = QCheckBox("Ctrl+Enter で送信")
        self.enter_to_send_checkbox = QCheckBox("Enter で送信")
        self.ctrl_enter_checkbox.setChecked(bool(self._config.ui_ctrl_enter_to_send))
        self.enter_to_send_checkbox.setChecked(bool(self._config.ui_enter_to_send))
        layout.addRow(self.ctrl_enter_checkbox)
        layout.addRow(self.enter_to_send_checkbox)

        # チャット挙動
        self.autoscroll_checkbox = QCheckBox("新しいメッセージで自動スクロール")
        self.autoscroll_checkbox.setChecked(bool(self._config.ui_autoscroll_enabled))
        layout.addRow(self.autoscroll_checkbox)

        self.streaming_stop_checkbox = QCheckBox("ストリーミング中に「停止」ボタンを表示")
        self.streaming_stop_checkbox.setChecked(bool(self._config.ui_streaming_stop_enabled))
        layout.addRow(self.streaming_stop_checkbox)

        self.streaming_chunk_interval_field = QSpinBox()
        self.streaming_chunk_interval_field.setRange(0, 1000)
        self.streaming_chunk_interval_field.setSingleStep(10)
        self.streaming_chunk_interval_field.setValue(int(self._config.ui_streaming_chunk_render_interval_ms or 0))
        layout.addRow("ストリーミング更新間隔 (ms):", self.streaming_chunk_interval_field)

        self.hotkey_enabled_checkbox = QCheckBox("グローバルホットキーでウィンドウを呼び出す")
        self.hotkey_enabled_checkbox.setChecked(bool(getattr(self._config, "global_hotkey_enabled", True)))
        layout.addRow(self.hotkey_enabled_checkbox)

        self.hotkey_combination_field = QLineEdit()
        self.hotkey_combination_field.setPlaceholderText("Ctrl+Alt+Space")
        self.hotkey_combination_field.setText(getattr(self._config, "global_hotkey_combination", "Ctrl+Alt+Space"))
        layout.addRow("ホットキー（例: Ctrl+Alt+Space）:", self.hotkey_combination_field)

        self.start_minimized_checkbox = QCheckBox("起動時にトレイへ格納して開始する")
        self.start_minimized_checkbox.setChecked(bool(getattr(self._config, "start_minimized_to_tray", False)))
        layout.addRow(self.start_minimized_checkbox)

        self.always_on_top_checkbox = QCheckBox("常に最前面に表示する")
        self.always_on_top_checkbox.setChecked(bool(getattr(self._config, "always_on_top", False)))
        layout.addRow(self.always_on_top_checkbox)

        self._tabs.addTab(tab, "チャット・挙動")

    def _init_history_tab(self) -> None:
        tab = QWidget()
        layout = QFormLayout(tab)

        # 履歴保存
        self.history_enabled_checkbox = QCheckBox("会話履歴をローカルに保存する（マルチセッション）")
        self.history_enabled_checkbox.setChecked(bool(self._config.history_enabled))
        layout.addRow(self.history_enabled_checkbox)

        self.history_format_combo = QComboBox()
        self.history_format_combo.addItems(["json", "markdown"])
        current_fmt = getattr(self._config, "history_format", "json")
        idx = self.history_format_combo.findText(current_fmt)
        if idx >= 0:
            self.history_format_combo.setCurrentIndex(idx)
        layout.addRow("履歴保存フォーマット:", self.history_format_combo)

        self.history_max_messages_spin = QSpinBox()
        self.history_max_messages_spin.setRange(50, 5000)
        self.history_max_messages_spin.setSingleStep(50)
        self.history_max_messages_spin.setValue(int(self._config.history_max_messages or 400))
        layout.addRow("履歴メッセージ数の目安:", self.history_max_messages_spin)

        self.history_max_chars_spin = QSpinBox()
        self.history_max_chars_spin.setRange(10_000, 2_000_000)
        self.history_max_chars_spin.setSingleStep(50_000)
        self.history_max_chars_spin.setValue(int(self._config.history_max_chars or 200_000))
        layout.addRow("履歴文字数の目安:", self.history_max_chars_spin)

        self._tabs.addTab(tab, "履歴・セッション")

    def _init_display_tab(self) -> None:
        tab = QWidget()
        layout = QFormLayout(tab)

        # フォントファミリ: OSインストールフォントから選択
        self.font_family_field = QFontComboBox()
        self.font_family_field.setEditable(False)
        current_family = self._config.ui_markdown_font_family or "Segoe UI"
        idx = self.font_family_field.findText(current_family)
        if idx >= 0:
            self.font_family_field.setCurrentIndex(idx)
        layout.addRow("Markdown フォントファミリ:", self.font_family_field)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 32)
        self.font_size_spin.setValue(int(self._config.ui_markdown_font_size_pt or 11))
        layout.addRow("Markdown フォントサイズ (pt):", self.font_size_spin)

        self.line_height_spin = QDoubleSpinBox()
        self.line_height_spin.setRange(1.0, 3.0)
        self.line_height_spin.setSingleStep(0.1)
        self.line_height_spin.setValue(float(self._config.ui_markdown_line_height or 1.6))
        layout.addRow("行間:", self.line_height_spin)

        self._tabs.addTab(tab, "表示・フォント")

    def _init_network_tab(self) -> None:
        tab = QWidget()
        layout = QFormLayout(tab)

        # タイムアウト（秒）
        self.request_timeout_field = QLineEdit()
        self.request_timeout_field.setText(str(int(self._config.request_timeout_ms / 1000)))
        layout.addRow("リクエストタイムアウト（秒）:", self.request_timeout_field)

        self.connect_timeout_field = QLineEdit()
        self.connect_timeout_field.setText(str(int(self._config.connect_timeout_ms / 1000)))
        layout.addRow("接続タイムアウト（秒）:", self.connect_timeout_field)

        self.stream_total_timeout_field = QLineEdit()
        self.stream_total_timeout_field.setText(str(int(self._config.stream_total_timeout_ms / 1000)))
        layout.addRow("ストリーム全体タイムアウト（秒）:", self.stream_total_timeout_field)

        self.stream_connect_timeout_field = QLineEdit()
        self.stream_connect_timeout_field.setText(str(int(self._config.stream_connect_timeout_ms / 1000)))
        layout.addRow("ストリーム接続タイムアウト（秒）:", self.stream_connect_timeout_field)

        self._tabs.addTab(tab, "ネットワーク")
    
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
        # 既存 profiles を使用（_finalize_config で更新済み）
        cfg = self._config

        # ネットワークタイムアウト（秒→ms）。無効入力は既定値を維持。
        def _parse_int(text: str, default: int) -> int:
            try:
                return max(1, int(text.strip()))
            except ValueError:
                return default

        cfg.request_timeout_ms = _parse_int(self.request_timeout_field.text(), int(cfg.request_timeout_ms / 1000)) * 1000
        cfg.connect_timeout_ms = _parse_int(self.connect_timeout_field.text(), int(cfg.connect_timeout_ms / 1000)) * 1000
        cfg.stream_total_timeout_ms = _parse_int(self.stream_total_timeout_field.text(), int(cfg.stream_total_timeout_ms / 1000)) * 1000
        cfg.stream_connect_timeout_ms = _parse_int(self.stream_connect_timeout_field.text(), int(cfg.stream_connect_timeout_ms / 1000)) * 1000

        # キーバインドは片方のみ有効にする（両方ONの場合は Ctrl+Enter 優先）
        ctrl_enter = self.ctrl_enter_checkbox.isChecked()
        enter_send = self.enter_to_send_checkbox.isChecked() and not ctrl_enter
        cfg.ui_ctrl_enter_to_send = ctrl_enter
        cfg.ui_enter_to_send = enter_send

        # チャット挙動
        cfg.ui_autoscroll_enabled = self.autoscroll_checkbox.isChecked()
        cfg.ui_streaming_stop_enabled = self.streaming_stop_checkbox.isChecked()
        cfg.ui_streaming_chunk_render_interval_ms = int(self.streaming_chunk_interval_field.value())
        cfg.global_hotkey_enabled = self.hotkey_enabled_checkbox.isChecked()
        hotkey_text = self.hotkey_combination_field.text().strip() or "Ctrl+Alt+Space"
        cfg.global_hotkey_combination = hotkey_text
        cfg.start_minimized_to_tray = self.start_minimized_checkbox.isChecked()
        cfg.always_on_top = self.always_on_top_checkbox.isChecked()

        # 表示・フォント
        # QFontComboBox から現在のフォントファミリ名を取得
        cfg.ui_markdown_font_family = (
            self.font_family_field.currentFont().family().strip() or "Segoe UI"
        )
        cfg.ui_markdown_font_size_pt = int(self.font_size_spin.value())
        cfg.ui_markdown_line_height = float(self.line_height_spin.value())

        # 履歴・セッション
        cfg.history_enabled = self.history_enabled_checkbox.isChecked()
        cfg.history_format = self.history_format_combo.currentText() or "json"
        cfg.history_max_messages = int(self.history_max_messages_spin.value())
        cfg.history_max_chars = int(self.history_max_chars_spin.value())
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
        self.resize(380, 220)
        self._config = config or Config()

        layout = QFormLayout(self)

        # ログ有効/無効
        self.logging_enabled_checkbox = QCheckBox("ログを有効化（推奨）")
        self.logging_enabled_checkbox.setChecked(bool(getattr(self._config, "logging_enabled", True)))
        layout.addRow(self.logging_enabled_checkbox)

        # 会話履歴の保存有無（マルチセッションの永続化）
        self.history_enabled_checkbox = QCheckBox("会話履歴をローカルに保存する（マルチセッション）")
        self.history_enabled_checkbox.setChecked(bool(getattr(self._config, "history_enabled", True)))
        layout.addRow(self.history_enabled_checkbox)

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
        self._config.history_enabled = self.history_enabled_checkbox.isChecked()
        self._config.diagnostics_show_env_details = self.env_details_checkbox.isChecked()
        self.accept()

    def get_config(self) -> Config:
        """更新済み Config を返す。"""
        return self._config

