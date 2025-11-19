"""Helpers for working with Markdown in QTextDocument contexts."""

from __future__ import annotations

from PySide6.QtGui import QTextCursor, QTextDocument, QTextDocumentFragment


def markdown_to_plain_text(markdown: str | None) -> str:
    """Convert Markdown to the plain text that QTextDocument would render."""
    doc = QTextDocument()
    doc.setMarkdown(markdown or "")
    return doc.toPlainText()


def markdown_to_fragment(markdown: str | None) -> QTextDocumentFragment:
    """Convert Markdown to a QTextDocumentFragment via Qt's parser."""
    doc = QTextDocument()
    doc.setMarkdown(markdown or "")
    cursor = QTextCursor(doc)
    cursor.select(QTextCursor.SelectionType.Document)
    return cursor.selection()

