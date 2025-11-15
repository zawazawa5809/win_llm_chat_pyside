"""検索 UI コンポーネント。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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


class SessionSearchBar(QWidget):
    """セッション内検索バー（Ctrl+F）。"""

    search_requested = Signal(str)
    next_requested = Signal()
    previous_requested = Signal()
    closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setVisible(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel("セッション内検索:")
        self._input = QLineEdit()
        self._input.setPlaceholderText("キーワードを入力（Enter: 次、Shift+Enter: 前）")
        self._input.returnPressed.connect(self.next_requested)
        self._input.textChanged.connect(self.search_requested)

        self._prev_button = QPushButton("前")
        self._prev_button.clicked.connect(self.previous_requested.emit)
        self._next_button = QPushButton("次")
        self._next_button.clicked.connect(self.next_requested.emit)

        self._status_label = QLabel("")
        self._status_label.setMinimumWidth(90)
        self._close_button = QToolButton()
        self._close_button.setText("×")
        self._close_button.clicked.connect(self._handle_close)

        layout.addWidget(self._label)
        layout.addWidget(self._input, stretch=1)
        layout.addWidget(self._prev_button)
        layout.addWidget(self._next_button)
        layout.addWidget(self._status_label)
        layout.addWidget(self._close_button)

    def show_bar(self) -> None:
        self.setVisible(True)
        self._input.setFocus()
        self._input.selectAll()

    def hide_bar(self) -> None:
        self.setVisible(False)

    def update_status(self, *, current: int, total: int) -> None:
        if total == 0:
            self._status_label.setText("0 / 0")
        else:
            self._status_label.setText(f"{current}/{total}")

    def clear(self) -> None:
        self._input.clear()

    def _handle_close(self) -> None:
        self.clear()
        self.hide_bar()
        self.closed.emit()


class AttachmentSearchPanel(QWidget):
    """添付テキスト検索と抜粋送信のパネル。"""

    search_requested = Signal(str)
    snippet_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_keyword: str = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("添付テキストを検索...")
        self._input.returnPressed.connect(self._emit_search)
        self._search_button = QPushButton("検索")
        self._search_button.clicked.connect(self._emit_search)
        header.addWidget(QLabel("添付検索:"))
        header.addWidget(self._input, stretch=1)
        header.addWidget(self._search_button)
        layout.addLayout(header)

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

    def _emit_search(self) -> None:
        self.search_requested.emit(self._input.text())

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


