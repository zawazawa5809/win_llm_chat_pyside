"""Build QTextDocument instances for the chat view with bubble styling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFrame,
    QTextFrameFormat,
    QTextLength,
)

from win_llm_chat_pyside.core.markdown_utils import markdown_to_fragment, markdown_to_plain_text
from win_llm_chat_pyside.models import Message
from win_llm_chat_pyside.ui.styles.theme import ThemeTokens, get_theme


@dataclass
class MessageDocumentRegion:
    """Represents the rendered region for a single Message."""

    message_index: int
    role: str
    start_position: int
    content_start_position: int
    end_position: int
    plain_text: str
    frame: QTextFrame | None


@dataclass
class ChatDocumentBuildResult:
    """Encapsulates the document and metadata used by the chat view."""

    document: QTextDocument
    message_regions: list[MessageDocumentRegion]


class ChatDocumentBuilder:
    """Constructs QTextDocuments that render chat history as rich text bubbles."""

    def __init__(self, *, theme: ThemeTokens | None = None, max_width_percent: float = 82.0) -> None:
        self._theme = theme or get_theme()
        self._max_width_percent = max(40.0, min(95.0, max_width_percent))

    def build(self, messages: Sequence[Message]) -> ChatDocumentBuildResult:
        """Build the QTextDocument and related metadata for a chat transcript."""
        document = QTextDocument()
        document.setDocumentMargin(0.0)
        document.setUseDesignMetrics(True)
        default_font = QFont(self._theme.typography.font_family, self._theme.typography.body_size)
        document.setDefaultFont(default_font)

        cursor = QTextCursor(document)
        regions: list[MessageDocumentRegion] = []

        for index, message in enumerate(messages):
            if index > 0:
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.insertBlock()
            region = self._insert_message(cursor, message, index)
            regions.append(region)
            cursor.movePosition(QTextCursor.MoveOperation.End)

        return ChatDocumentBuildResult(document=document, message_regions=regions)

    # --------------------------------------------------------------------- helpers
    def _insert_message(self, cursor: QTextCursor, message: Message, index: int) -> MessageDocumentRegion:
        frame = self._begin_bubble_frame(cursor, message)
        frame_cursor = QTextCursor(frame)

        self._insert_role_label(frame_cursor, message)
        frame_cursor.insertBlock()
        content_start = frame_cursor.position()

        fragment = markdown_to_fragment(message.content or "")
        frame_cursor.insertFragment(fragment)

        plain_text = markdown_to_plain_text(message.content or "")
        start = frame.firstCursorPosition().position()
        end = frame.lastCursorPosition().position()

        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertBlock()  # ensure next frame starts on a new line

        return MessageDocumentRegion(
            message_index=index,
            role=message.role,
            start_position=start,
            content_start_position=content_start,
            end_position=end,
            plain_text=plain_text,
            frame=frame,
        )

    def _begin_bubble_frame(self, cursor: QTextCursor, message: Message) -> QTextFrame:
        frame_format = QTextFrameFormat()
        frame_format.setBorder(0.0)
        frame_format.setPadding(float(self._theme.spacing.bubble_padding))
        frame_format.setWidth(QTextLength(QTextLength.PercentageLength, self._max_width_percent))
        frame_format.setBackground(QColor(self._bubble_bg_color(message.role)))
        frame_format.setForeground(QColor(self._bubble_fg_color(message.role)))
        frame_format.setTopMargin(float(self._theme.spacing.bubble_gap))
        frame_format.setBottomMargin(float(self._theme.spacing.bubble_gap))
        frame_format.setLeftMargin(float(self._left_margin_for_role(message.role)))
        frame_format.setRightMargin(float(self._right_margin_for_role(message.role)))
        frame_format.setBorderStyle(QTextFrameFormat.BorderStyle.BorderStyle_None)
        frame_format.setPosition(self._frame_position_for_role(message.role))
        return cursor.insertFrame(frame_format)

    def _insert_role_label(self, cursor: QTextCursor, message: Message) -> None:
        label_text = self._display_role(message.role)
        if not label_text:
            return
        block_format = QTextBlockFormat()
        block_format.setAlignment(Qt.AlignmentFlag.AlignLeft)
        cursor.setBlockFormat(block_format)
        label_format = QTextCharFormat()
        label_format.setFontPointSize(float(self._theme.typography.caption_size))
        label_format.setForeground(QColor(self._theme.colors.bubble_meta_text))
        cursor.setCharFormat(label_format)
        cursor.insertText(label_text)

    def _frame_position_for_role(self, role: str) -> QTextFrameFormat.Position:
        if role == "user":
            return QTextFrameFormat.Position.FloatRight
        if role == "assistant":
            return QTextFrameFormat.Position.FloatLeft
        return QTextFrameFormat.Position.InFlow

    def _left_margin_for_role(self, role: str) -> int:
        spacing = self._theme.spacing
        if role == "user":
            return spacing.lg
        if role == "assistant":
            return spacing.sm
        return spacing.md

    def _right_margin_for_role(self, role: str) -> int:
        spacing = self._theme.spacing
        if role == "user":
            return spacing.sm
        if role == "assistant":
            return spacing.lg
        return spacing.md

    def _bubble_bg_color(self, role: str) -> str:
        colors = self._theme.colors
        if role == "user":
            return colors.bubble_user_bg
        if role == "assistant":
            return colors.bubble_assistant_bg
        return colors.bubble_system_bg

    def _bubble_fg_color(self, role: str) -> str:
        colors = self._theme.colors
        if role == "user":
            return colors.bubble_user_text
        if role == "assistant":
            return colors.bubble_assistant_text
        return colors.bubble_system_text

    def _display_role(self, role: str) -> str:
        if role == "user":
            return "User"
        if role == "assistant":
            return "Assistant"
        if role == "system":
            return "System"
        return role.title()
