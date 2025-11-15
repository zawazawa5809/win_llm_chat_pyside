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
    question_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["ファイル名", "状態", "詳細"])
        self._tree.setColumnWidth(0, 220)
        self._tree.setSelectionMode(QTreeWidget.SingleSelection)

        self._attach_button = QPushButton("ファイルを添付")
        self._summarize_button = QPushButton("要約")
        self._question_button = QPushButton("質問する")
        self._remove_button = QPushButton("削除")

        self._attach_button.clicked.connect(self.attach_requested)
        self._summarize_button.clicked.connect(self._emit_summarize)
        self._question_button.clicked.connect(self._emit_question)
        self._remove_button.clicked.connect(self._emit_remove)

        button_row = QHBoxLayout()
        button_row.addWidget(self._attach_button)
        button_row.addWidget(self._summarize_button)
        button_row.addWidget(self._question_button)
        button_row.addWidget(self._remove_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tree, stretch=1)
        layout.addLayout(button_row)

        self._attachments: list[AttachmentMetadata] = []

    def set_attachments(self, attachments: list[AttachmentMetadata]) -> None:
        self._attachments = list(attachments)
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
            self._tree.addTopLevelItem(item)
        self._tree.expandAll()

    def current_attachment_id(self) -> str | None:
        item = self._tree.currentItem()
        if not item:
            return None
        return item.data(0, Qt.UserRole)

    def _emit_summarize(self) -> None:
        attachment_id = self.current_attachment_id()
        if not attachment_id:
            QMessageBox.information(self, "添付ファイル", "要約するファイルを選択してください。")
            return
        self.summarize_requested.emit(attachment_id)

    def _emit_question(self) -> None:
        attachment_id = self.current_attachment_id()
        if not attachment_id:
            QMessageBox.information(self, "添付ファイル", "質問するファイルを選択してください。")
            return
        self.question_requested.emit(attachment_id)

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
        return " / ".join(details)


