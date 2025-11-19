"""検索 UI コンポーネント。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QLabel,
    QPushButton,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
)


class SearchBarBase(QWidget):
    """検索バーの共通 UI。"""

    search_requested = Signal(str)
    next_requested = Signal()
    previous_requested = Signal()
    closed = Signal()

    def __init__(
        self,
        *,
        label_text: str,
        placeholder_text: str,
        show_navigation: bool = True,
        show_close_button: bool = True,
        auto_search: bool = True,
        search_button_text: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._show_navigation = show_navigation
        self._show_close_button = show_close_button
        self._auto_search = auto_search
        self._search_button_text = search_button_text

        self._build_ui(label_text, placeholder_text)
        self._configure_connections()

    def _build_ui(self, label_text: str, placeholder_text: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._label = QLabel(label_text)
        layout.addWidget(self._label)

        self._input = QLineEdit()
        self._input.setObjectName("search-input")
        self._input.setPlaceholderText(placeholder_text)
        layout.addWidget(self._input, stretch=1)

        if self._search_button_text:
            self._search_button = QPushButton(self._search_button_text)
            self._search_button.setObjectName("search-button")
            layout.addWidget(self._search_button)
        else:
            self._search_button = None

        self._prev_button = QPushButton("前")
        self._prev_button.setObjectName("search-prev-button")
        self._next_button = QPushButton("次")
        self._next_button.setObjectName("search-next-button")
        if self._show_navigation:
            layout.addWidget(self._prev_button)
            layout.addWidget(self._next_button)
        else:
            self._prev_button.hide()
            self._next_button.hide()

        self._status_label = QLabel("0 / 0")
        self._status_label.setObjectName("search-status")
        self._status_label.setMinimumWidth(70)
        layout.addWidget(self._status_label)

        self._close_button = QToolButton()
        self._close_button.setObjectName("search-close-button")
        self._close_button.setText("×")
        if self._show_close_button:
            layout.addWidget(self._close_button)
        else:
            self._close_button.hide()

        self._esc_shortcut = QShortcut(QKeySequence("Esc"), self)
        self._esc_shortcut.setEnabled(not self._show_close_button)

    def _configure_connections(self) -> None:
        if self._auto_search:
            self._input.textChanged.connect(self.search_requested.emit)
        else:
            self._input.returnPressed.connect(self._emit_search_on_enter)
        if self._search_button is not None:
            self._search_button.clicked.connect(self._emit_search_on_enter)

        if self._show_navigation:
            self._next_button.clicked.connect(self.next_requested.emit)
            self._prev_button.clicked.connect(self.previous_requested.emit)
            self._next_shortcut = QShortcut(QKeySequence("Return"), self._input)
            self._next_shortcut.activated.connect(self.next_requested.emit)
            self._prev_shortcut = QShortcut(QKeySequence("Shift+Return"), self._input)
            self._prev_shortcut.activated.connect(self.previous_requested.emit)
        else:
            self._next_shortcut = None
            self._prev_shortcut = None

        if self._show_close_button:
            self._close_button.clicked.connect(self._handle_close)
            self._esc_shortcut.activated.connect(self._handle_close)
        else:
            self._esc_shortcut.activated.connect(self.clear)

    # --- public helpers -------------------------------------------------
    def show_bar(self) -> None:
        self.setVisible(True)
        if self._show_close_button:
            self._esc_shortcut.setEnabled(True)
        self._input.setFocus(Qt.ShortcutFocusReason)
        self._input.selectAll()

    def hide_bar(self) -> None:
        self.setVisible(False)
        if self._show_close_button:
            self._esc_shortcut.setEnabled(False)

    def clear(self) -> None:
        self._input.clear()
        self.update_status(current=0, total=0)

    def update_status(self, *, current: int, total: int) -> None:
        self._status_label.setText(f"{current} / {total}" if total else "0 / 0")

    def line_edit(self) -> QLineEdit:
        return self._input

    def next_button(self) -> QPushButton:
        return self._next_button

    def previous_button(self) -> QPushButton:
        return self._prev_button

    def status_label(self) -> QLabel:
        return self._status_label

    def close_button(self) -> QToolButton:
        return self._close_button

    # --- internal slots --------------------------------------------------
    def _emit_search_on_enter(self) -> None:
        self.search_requested.emit(self._input.text())

    def _handle_close(self) -> None:
        self.clear()
        self.hide_bar()
        self.closed.emit()


class SessionSearchBar(SearchBarBase):
    """セッション内検索バー（Ctrl+F）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            label_text="セッション内検索:",
            placeholder_text="キーワードを入力（Enter: 次、Shift+Enter: 前、ESC: 閉じる）",
            show_navigation=True,
            show_close_button=True,
            auto_search=True,
            parent=parent,
        )
        self.setVisible(False)


class AttachmentSearchPanel(QWidget):
    """添付テキスト検索と抜粋送信のパネル。"""

    search_requested = Signal(str)
    snippet_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_keyword: str = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._search_bar = SearchBarBase(
            label_text="添付検索:",
            placeholder_text="添付テキストを検索... (Enter: 検索、ESC: 閉じる)",
            show_navigation=False,
            show_close_button=True,
            auto_search=False,
            search_button_text="検索",
            parent=self,
        )
        self._search_bar.search_requested.connect(self.search_requested.emit)
        self._search_bar.closed.connect(self._handle_close)
        layout.addWidget(self._search_bar)

        self._results = QTreeWidget()
        self._results.setHeaderLabels(["ファイル名", "ヒット数", "抜粋"])
        self._results.setColumnWidth(0, 180)
        self._results.setColumnWidth(1, 70)
        self._results.itemDoubleClicked.connect(self._emit_snippet)
        layout.addWidget(self._results, stretch=1)

        footer = QHBoxLayout()
        self._status_label = QLabel("")
        self._send_button = QPushButton("抜粋を入力欄へ挿入")
        self._send_button.clicked.connect(self._emit_snippet)
        footer.addWidget(self._status_label, stretch=1)
        footer.addWidget(self._send_button)
        layout.addLayout(footer)

    @property
    def current_keyword(self) -> str:
        return self._current_keyword

    def set_attachments_available(self, available: bool) -> None:
        self.setEnabled(available)
        if not available:
            self._results.clear()
            self._status_label.setText("添付ファイルがありません")
        elif not self.isVisible():
            self._status_label.setText("")

    def show_panel(self) -> None:
        self.setVisible(True)
        self._search_bar.show_bar()

    def hide_panel(self) -> None:
        self.setVisible(False)
        self._search_bar.hide_bar()

    def focus_search_input(self) -> None:
        """Focus the search input regardless of visibility state."""

        self._search_bar.show_bar()
        self._search_bar.line_edit().setFocus(Qt.ShortcutFocusReason)
        self._search_bar.line_edit().selectAll()

    def _handle_close(self) -> None:
        self.hide_panel()
        self._search_bar.clear()

    def update_results(self, keyword: str, results) -> None:
        self._current_keyword = keyword
        self._results.clear()
        for hit in results:
            attachment_id = getattr(hit, "attachment_id", None)
            filename = getattr(hit, "filename", "")
            hit_count = getattr(hit, "hit_count", 0)
            snippet = getattr(hit, "snippet", "")
            item = QTreeWidgetItem(
                [
                    filename,
                    str(hit_count),
                    snippet,
                ]
            )
            item.setData(0, Qt.UserRole, attachment_id)
            item.setData(0, Qt.UserRole + 1, snippet)
            self._results.addTopLevelItem(item)
        self._status_label.setText(f"{len(results)} 件ヒット" if results else "一致なし")

    def _emit_snippet(self) -> None:
        item = self._results.currentItem()
        if not item:
            QMessageBox.information(self, "添付検索", "抜粋を選択してください。")
            return
        attachment_id = item.data(0, Qt.UserRole)
        snippet = item.data(0, Qt.UserRole + 1) or ""
        if not attachment_id:
            QMessageBox.information(self, "添付検索", "抜粋を選択してください。")
            return
        self.snippet_requested.emit(attachment_id, str(snippet))

