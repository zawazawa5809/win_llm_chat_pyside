"""Main layout container that manages sidebar/chat panel split."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QSplitter, QWidget

from win_llm_chat_pyside.models.layout_mode import LayoutMode
from win_llm_chat_pyside.ui.styles.theme import ThemeTokens, build_main_container_styles, get_theme


class MainLayoutContainer(QWidget):
    """Wraps the sidebar/chat panel splitter and applies layout modes."""

    DEFAULT_SIDEBAR_WIDTH = 260
    COMPACT_SIDEBAR_WIDTH = 0
    MIN_CHAT_WIDTH = 420

    def __init__(
        self,
        sidebar_widget: QWidget,
        content_widget: QWidget,
        parent: QWidget | None = None,
        *,
        theme: ThemeTokens | None = None,
    ) -> None:
        super().__init__(parent)
        self._sidebar = sidebar_widget
        self._sidebar.setObjectName("sidebarPane")
        self._content = content_widget
        self._content.setObjectName("chatPane")
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._splitter.addWidget(self._sidebar)
        self._splitter.addWidget(self._content)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._splitter)
        self._current_mode: LayoutMode = LayoutMode.FOCUSED
        self._stored_sidebar_width: int = self.DEFAULT_SIDEBAR_WIDTH
        self._applied_sidebar_width: int = self.DEFAULT_SIDEBAR_WIDTH
        self._theme = theme or get_theme()
        self._apply_sizes_for_mode(self._current_mode)
        self.apply_theme(self._theme)

    @property
    def current_mode(self) -> LayoutMode:
        return self._current_mode

    def set_layout_mode(self, mode: LayoutMode) -> None:
        if mode == self._current_mode:
            return
        if mode is LayoutMode.COMPACT:
            self._stored_sidebar_width = max(self.sidebar_width(), self.DEFAULT_SIDEBAR_WIDTH)
        self._current_mode = mode
        self._apply_sizes_for_mode(mode)

    def sidebar_width(self) -> int:
        return self._applied_sidebar_width

    def _apply_sizes_for_mode(self, mode: LayoutMode) -> None:
        total_width = sum(self._splitter.sizes())
        if total_width <= 0:
            total_width = self.DEFAULT_SIDEBAR_WIDTH + self.MIN_CHAT_WIDTH
        if mode is LayoutMode.COMPACT:
            sidebar_width = self.COMPACT_SIDEBAR_WIDTH
        else:
            sidebar_width = max(self._stored_sidebar_width, self.DEFAULT_SIDEBAR_WIDTH)
        chat_width = max(self.MIN_CHAT_WIDTH, total_width - sidebar_width)
        self._splitter.setSizes([sidebar_width, chat_width])
        self._applied_sidebar_width = sidebar_width

    def apply_theme(self, theme: ThemeTokens) -> None:
        """Apply theme colors to sidebar/chat areas."""
        self._theme = theme
        self.setStyleSheet(build_main_container_styles(theme))


