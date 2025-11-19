"""LayoutMode enum shared between config persistence and UI components."""

from __future__ import annotations

from enum import Enum


class LayoutMode(str, Enum):
    """UI layout modes for the main window."""

    FOCUSED = "focused"
    COMPACT = "compact"

    @classmethod
    def from_value(cls, value: str | None) -> "LayoutMode":
        """Convert arbitrary value to a LayoutMode, defaulting to FOCUSED."""
        if not value:
            return cls.FOCUSED
        try:
            return cls(value)
        except ValueError:
            return cls.FOCUSED


