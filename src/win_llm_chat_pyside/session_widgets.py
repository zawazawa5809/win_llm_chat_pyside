"""
セッション一覧 UI コンポーネント。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QMessageBox,
)

from .models import SessionMeta


class SessionListPanel(QWidget):
    """セッション一覧と操作ボタンを提供するパネル。"""

    session_selected = Signal(str)
    create_requested = Signal()
    rename_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_selection_changed)
        self._metas: list[SessionMeta] = []

        self._create_button = QPushButton("新規")
        self._rename_button = QPushButton("名前変更")
        self._delete_button = QPushButton("削除")

        self._create_button.clicked.connect(self.create_requested)
        self._rename_button.clicked.connect(self._emit_rename)
        self._delete_button.clicked.connect(self._emit_delete)

        layout = QVBoxLayout(self)
        layout.addWidget(self._list, stretch=1)

        button_row = QHBoxLayout()
        button_row.addWidget(self._create_button)
        button_row.addWidget(self._rename_button)
        button_row.addWidget(self._delete_button)
        layout.addLayout(button_row)

        self.setMinimumWidth(220)

    def set_sessions(self, metas: list[SessionMeta], active_id: str | None) -> None:
        self._metas = list(metas)
        self._list.blockSignals(True)
        self._list.clear()
        for meta in metas:
            item = QListWidgetItem(meta.name)
            item.setData(Qt.UserRole, meta.id)
            item.setToolTip(meta.name)
            self._list.addItem(item)
        self._list.blockSignals(False)
        if active_id:
            self.set_active_session(active_id)
        elif metas:
            self.set_active_session(metas[0].id)

    def set_active_session(self, session_id: str) -> None:
        self._list.blockSignals(True)
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item.data(Qt.UserRole) == session_id:
                self._list.setCurrentRow(row)
                break
        self._list.blockSignals(False)

    def current_session_id(self) -> str | None:
        item = self._list.currentItem()
        if not item:
            return None
        return item.data(Qt.UserRole)

    def _emit_rename(self) -> None:
        session_id = self.current_session_id()
        if not session_id:
            QMessageBox.information(self, "セッション", "名前を変更するセッションを選択してください。")
            return
        self.rename_requested.emit(session_id)

    def _emit_delete(self) -> None:
        session_id = self.current_session_id()
        if not session_id:
            QMessageBox.information(self, "セッション", "削除するセッションを選択してください。")
            return
        self.delete_requested.emit(session_id)

    def _on_selection_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:  # noqa: ARG002
        if not current:
            return
        session_id = current.data(Qt.UserRole)
        if session_id:
            self.session_selected.emit(session_id)



