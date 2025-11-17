"""Controller to manage chat view scrolling behavior."""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QTextBrowser, QScrollBar


class ChatScrollController(QObject):
    """Tracks user initiated scrolls and performs conditional auto scroll."""

    def __init__(self, chat_view: QTextBrowser, *, auto_scroll_enabled: bool = True) -> None:
        super().__init__(chat_view)
        self._chat_view = chat_view
        self._scrollbar: QScrollBar = chat_view.verticalScrollBar()
        self._auto_scroll_enabled = auto_scroll_enabled
        self._user_override = False
        self._scrollbar.valueChanged.connect(self._on_scroll_value_changed)

    def set_auto_scroll_enabled(self, enabled: bool) -> None:
        self._auto_scroll_enabled = enabled
        if enabled and not self._user_override:
            self.scroll_to_end(force=True)

    def scroll_to_end(self, *, force: bool = False) -> None:
        if not self._auto_scroll_enabled and not force:
            return
        if self._user_override and not force:
            return
        self._scrollbar.setValue(self._scrollbar.maximum())
        self._user_override = False

    def _on_scroll_value_changed(self, value: int) -> None:
        max_value = self._scrollbar.maximum()
        self._user_override = value < max_value

