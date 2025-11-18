"""添付ファイル一覧と操作 UI コンポーネント。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
)

from .models import AttachmentMetadata


class AttachmentListWidget(QWidget):
    """セッションに紐づく添付ファイルの一覧と操作を提供するウィジェット。"""

    attach_requested = Signal()
    remove_requested = Signal(str)
    summarize_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["ファイル名", "状態", "詳細"])
        self._tree.setColumnWidth(0, 220)
        self._tree.setSelectionMode(QTreeWidget.SingleSelection)
        self._tree.itemChanged.connect(self._on_item_changed)

        self._attach_button = QPushButton("ファイルを添付")
        self._summarize_button = QPushButton("要約")
        self._clear_selection_button = QPushButton("選択解除")
        self._remove_button = QPushButton("削除")

        self._attach_button.clicked.connect(self.attach_requested)
        self._summarize_button.clicked.connect(self._emit_summarize)
        self._remove_button.clicked.connect(self._emit_remove)
        self._clear_selection_button.clicked.connect(self.clear_send_selection)

        button_row = QHBoxLayout()
        button_row.addWidget(self._attach_button)
        button_row.addWidget(self._summarize_button)
        button_row.addWidget(self._clear_selection_button)
        button_row.addWidget(self._remove_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tree, stretch=1)
        layout.addLayout(button_row)

        self._attachments: list[AttachmentMetadata] = []
        self._selected_attachment_ids: set[str] = set()

    def set_attachments(self, attachments: list[AttachmentMetadata]) -> None:
        self._attachments = list(attachments)
        valid_ids = {attachment.id for attachment in attachments}
        self._selected_attachment_ids.intersection_update(valid_ids)

        self._tree.blockSignals(True)
        self._tree.clear()
        for attachment in attachments:
            item = QTreeWidgetItem(
                [
                    attachment.filename,
                    self._status_label(attachment),
                    self._detail_text(attachment),
                ]
            )
            item.setData(0, Qt.UserRole, attachment.id)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            check_state = Qt.Checked if attachment.id in self._selected_attachment_ids else Qt.Unchecked
            item.setCheckState(0, check_state)
            self._tree.addTopLevelItem(item)
        self._tree.blockSignals(False)
        self._tree.expandAll()

    def current_attachment_id(self) -> str | None:
        item = self._tree.currentItem()
        if not item:
            return None
        return item.data(0, Qt.UserRole)

    def focus_preferred_item(self) -> None:
        """Ensure at least one attachment is focused and scrolled into view."""

        if self._tree.topLevelItemCount() == 0:
            self._tree.clearSelection()
            self.setFocus(Qt.FocusReason.OtherFocusReason)
            return
        item = self._tree.currentItem()
        if item is None:
            item = self._tree.topLevelItem(0)
            if item:
                self._tree.setCurrentItem(item)
        if item:
            self._tree.scrollToItem(item)
        self._tree.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _emit_summarize(self) -> None:
        attachment_id = self.current_attachment_id()
        if not attachment_id:
            QMessageBox.information(self, "添付ファイル", "要約するファイルを選択してください。")
            return
        self.summarize_requested.emit(attachment_id)

    def _emit_remove(self) -> None:
        attachment_id = self.current_attachment_id()
        if not attachment_id:
            QMessageBox.information(self, "添付ファイル", "削除するファイルを選択してください。")
            return
        self.remove_requested.emit(attachment_id)

    @staticmethod
    def _status_label(attachment: AttachmentMetadata) -> str:
        mapping = {
            "pending": "待機中",
            "extracting": "抽出中",
            "ready": "利用可能",
            "failed": "失敗",
        }
        return mapping.get(attachment.status, attachment.status)

    @staticmethod
    def _detail_text(attachment: AttachmentMetadata) -> str:
        details: list[str] = []
        if attachment.text_length:
            details.append(f"{attachment.text_length} 文字")
        if attachment.page_count:
            details.append(f"{attachment.page_count} ページ")
        if attachment.length_warning:
            details.append("長文注意")
        if attachment.error_message:
            details.append(f"エラー: {attachment.error_message}")
        if attachment.source == "clipboard_image":
            details.append("画像")
        return " / ".join(details)

    def selected_attachment_ids(self) -> list[str]:
        """現在送信対象として選択されている添付 ID を表示順に返す。"""

        ordered_ids: list[str] = []
        for index in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(index)
            if item and item.checkState(0) == Qt.Checked:
                attachment_id = item.data(0, Qt.UserRole)
                if attachment_id:
                    ordered_ids.append(attachment_id)
        return ordered_ids

    def clear_send_selection(self) -> None:
        """送信対象の選択状態をクリアする。"""

        if not self._selected_attachment_ids:
            return
        self._selected_attachment_ids.clear()
        self._tree.blockSignals(True)
        for index in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(index)
            if item:
                item.setCheckState(0, Qt.Unchecked)
        self._tree.blockSignals(False)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if column != 0:
            return
        attachment_id = item.data(0, Qt.UserRole)
        if not attachment_id:
            return
        if item.checkState(0) == Qt.Checked:
            self._selected_attachment_ids.add(attachment_id)
        else:
            self._selected_attachment_ids.discard(attachment_id)


