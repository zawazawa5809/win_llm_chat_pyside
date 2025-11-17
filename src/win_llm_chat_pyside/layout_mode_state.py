"""State helper for managing layout mode selection and persistence."""

from __future__ import annotations

from .config import Config
from .layout_mode import LayoutMode


class LayoutModeState:
    """Encapsulates layout mode selection based on the active Config."""

    def __init__(self, config: Config) -> None:
        self._config = config

    @property
    def mode(self) -> LayoutMode:
        """Return the currently selected layout mode."""
        return LayoutMode.from_value(getattr(self._config, "layout_mode", LayoutMode.FOCUSED.value))

    def set_mode(self, mode: LayoutMode) -> LayoutMode:
        """Set layout mode explicitly."""
        self._config.layout_mode = mode.value
        return mode

    def toggle(self) -> LayoutMode:
        """Toggle between focused and compact modes."""
        new_mode = LayoutMode.COMPACT if self.mode is LayoutMode.FOCUSED else LayoutMode.FOCUSED
        self._config.layout_mode = new_mode.value
        return new_mode

