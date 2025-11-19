"""Controller to manage chat view scrolling behavior."""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QAbstractScrollArea, QScrollBar


class ChatScrollController(QObject):
    """Tracks user initiated scrolls and performs conditional auto scroll."""

    def __init__(self, chat_view: QAbstractScrollArea, *, auto_scroll_enabled: bool = True) -> None:
        super().__init__(chat_view)
        self._chat_view = chat_view
        self._scrollbar: QScrollBar = chat_view.verticalScrollBar()
        self._auto_scroll_enabled = auto_scroll_enabled
        self._user_override = False
        self._suspend_tracking = False
        self._scrollbar.valueChanged.connect(self._on_scroll_value_changed)

    def set_auto_scroll_enabled(self, enabled: bool) -> None:
        self._auto_scroll_enabled = enabled
        if enabled and not self._user_override:
            self.scroll_to_end(force=True)

    @property
    def is_user_override(self) -> bool:
        """ユーザーが手動スクロールで自動追従を無効化しているかどうか。"""
        return self._user_override

    def scroll_to_end(self, *, force: bool = False) -> None:
        if not self._auto_scroll_enabled and not force:
            return
        if self._user_override and not force:
            return
        self._scrollbar.setValue(self._scrollbar.maximum())
        self._user_override = False

    # --- tracking control -------------------------------------------------
    def suspend_user_tracking(self) -> None:
        """Temporarily ignore scroll changes (e.g., during programmatic rebuilds)."""
        self._suspend_tracking = True

    def resume_user_tracking(self) -> None:
        self._suspend_tracking = False

    def _on_scroll_value_changed(self, value: int) -> None:
        if self._suspend_tracking:
            return
        max_value = self._scrollbar.maximum()
        # ユーザーが「末尾より上」を見始めたら override を有効化する。
        # 底に戻ったかどうかは別途 scroll_to_end(force=...) 側で制御する。
        if value < max_value:
            self._user_override = True

