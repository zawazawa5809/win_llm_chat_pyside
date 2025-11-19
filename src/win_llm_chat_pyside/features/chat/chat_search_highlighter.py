"""Apply session search highlights onto ChatRichTextView."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit

from win_llm_chat_pyside.features.chat.chat_rich_text_view import ChatRichTextView
from win_llm_chat_pyside.features.chat.chat_document_builder import MessageDocumentRegion
from win_llm_chat_pyside.features.search.search_services import SessionHit


class ChatSearchHighlighter:
    """Manage text highlights for session search hits."""

    def __init__(self, view: ChatRichTextView, *, highlight_color: str = "#3f51b5") -> None:
        self._view = view
        self._highlight_brush = QColor(highlight_color)
        self._hits: list[SessionHit] = []

    def apply_hits(self, hits: Sequence[SessionHit]) -> None:
        """Apply highlight overlay for the provided search hits."""
        self._hits = list(hits)
        selections: list[QTextEdit.ExtraSelection] = []
        for hit in hits:
            cursor = self._cursor_for_hit(hit)
            if cursor is None:
                continue
            selection = QTextEdit.ExtraSelection()
            highlight_format = QTextCharFormat()
            highlight_format.setBackground(self._highlight_brush)
            selection.cursor = cursor
            selection.format = highlight_format
            selections.append(selection)
        self._view.setExtraSelections(selections)

    def clear(self) -> None:
        """Remove existing highlights."""
        self._hits.clear()
        self._view.setExtraSelections([])

    def focus_hit(self, index: int) -> None:
        """Focus and scroll to a specific hit."""
        if index < 0 or index >= len(self._hits):
            return
        cursor = self._cursor_for_hit(self._hits[index])
        if cursor is None:
            return
        self._view.setTextCursor(cursor)
        self._view.ensureCursorVisible()

    # ------------------------------------------------------------------ helpers
    def _region_for_hit(self, hit: SessionHit) -> MessageDocumentRegion | None:
        regions = self._view.message_regions
        if hit.message_index < 0 or hit.message_index >= len(regions):
            return None
        return regions[hit.message_index]

    def _cursor_for_hit(self, hit: SessionHit) -> QTextCursor | None:
        document = self._view.document()
        if document is None:
            return None
        region = self._region_for_hit(hit)
        if region is None:
            return None
        if hit.start < 0:
            return None
        if hit.start + hit.length > len(region.plain_text):
            return None
        start_position = region.content_start_position + hit.start
        cursor = QTextCursor(document)
        cursor.setPosition(start_position)
        cursor.movePosition(
            QTextCursor.MoveOperation.Right,
            QTextCursor.MoveMode.KeepAnchor,
            max(0, hit.length),
        )
        return cursor

