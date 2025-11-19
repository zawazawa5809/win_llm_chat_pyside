"""QTextBrowser-based chat view that renders messages via ChatDocumentBuilder."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtGui import QTextCursor, QTextDocument
from PySide6.QtWidgets import QTextBrowser

from win_llm_chat_pyside.features.chat.chat_document_builder import (
    ChatDocumentBuilder,
    ChatDocumentBuildResult,
    MessageDocumentRegion,
)
from win_llm_chat_pyside.models import Message
from win_llm_chat_pyside.ui.styles.theme import ThemeTokens, get_theme


class ChatRichTextView(QTextBrowser):
    """Rich text chat view that preserves Markdown and enables text selection."""

    def __init__(
        self,
        *,
        builder: ChatDocumentBuilder | None = None,
        theme: ThemeTokens | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._theme = theme or get_theme()
        self._builder = builder or ChatDocumentBuilder(theme=self._theme)
        self._messages: list[Message] = []
        self._document_result: ChatDocumentBuildResult | None = None
        self._message_regions: list[MessageDocumentRegion] = []
        self._document: QTextDocument | None = None

        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setOpenExternalLinks(False)
        self.setOpenLinks(False)
        self.setStyleSheet(f"background-color: {self._theme.colors.chat_bg}; border: none;")

    # ------------------------------------------------------------------ properties
    @property
    def message_count(self) -> int:
        return len(self._messages)

    @property
    def message_regions(self) -> list[MessageDocumentRegion]:
        return list(self._message_regions)

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    @property
    def document_result(self) -> ChatDocumentBuildResult | None:
        return self._document_result

    # -------------------------------------------------------------------- operations
    def set_messages(self, messages: Sequence[Message]) -> None:
        self._messages = list(messages)
        self._rebuild_document()

    def append_message(self, message: Message) -> None:
        self._messages.append(message)
        self._rebuild_document()

    def replace_last_message(self, message: Message) -> None:
        if not self._messages:
            self.append_message(message)
            return
        self._messages[-1] = message
        self._rebuild_document()

    def replace_message_content(self, index: int, content: str) -> None:
        if index < 0 or index >= len(self._messages):
            return
        role = self._messages[index].role
        self._messages[index] = Message(role=role, content=content)
        self._rebuild_document()

    def clear_messages(self) -> None:
        self._messages.clear()
        self._message_regions = []
        self._document_result = None
        empty_doc = QTextDocument()
        self._document = empty_doc
        self.setDocument(empty_doc)

    def rebuild(self) -> None:
        """Force reconstruction of the current messages (used by streaming)."""
        self._rebuild_document()

    # ---------------------------------------------------------------------- helpers
    def _rebuild_document(self) -> None:
        # 既存のスクロール位置を覚えておき、再構築後に近い位置へ復元する
        scrollbar = self.verticalScrollBar()
        old_max = scrollbar.maximum()
        old_value = scrollbar.value()

        result = self._builder.build(self._messages)
        self._document_result = result
        self._document = result.document
        self._message_regions = result.message_regions
        self.setDocument(self._document)

        new_max = scrollbar.maximum()
        if old_max > 0 and new_max > 0:
            # 比率ベースで位置を復元（ユーザーが中ほどを見ている場合に有効）
            ratio = max(0.0, min(1.0, old_value / old_max))
            scrollbar.setValue(int(new_max * ratio))
        else:
            # 初期表示など、履歴がない場合は末尾へ
            self.moveCursor(QTextCursor.MoveOperation.End)


