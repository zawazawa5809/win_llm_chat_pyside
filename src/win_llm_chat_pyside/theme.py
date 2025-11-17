"""Theme tokens and helpers for styling UI components."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class ColorTokens:
    chat_bg: str = "#1f1f23"
    chat_text: str = "#f3f3f4"
    sidebar_bg: str = "#18181b"
    sidebar_text: str = "#d0d0d5"
    composer_bg: str = "#202126"
    accent: str = "#2f6fff"
    border_subtle: str = "#2c2e34"
    surface_hover: str = "#3b3d44"


@dataclass(frozen=True)
class TypographyTokens:
    font_family: str = "Segoe UI"
    body_size: int = 11
    caption_size: int = 10


@dataclass(frozen=True)
class SpacingTokens:
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16


@dataclass(frozen=True)
class ThemeTokens:
    colors: ColorTokens
    typography: TypographyTokens
    spacing: SpacingTokens


class ThemeRole(str, Enum):
    CHAT = "chat"
    SIDEBAR = "sidebar"
    COMPOSER = "composer"


_DEFAULT_THEME = ThemeTokens(
    colors=ColorTokens(),
    typography=TypographyTokens(),
    spacing=SpacingTokens(),
)


def get_theme() -> ThemeTokens:
    """Return the default (current) theme tokens."""
    return _DEFAULT_THEME


def build_composer_styles(theme: ThemeTokens) -> str:
    """Build stylesheet for MessageComposerWidget."""
    colors = theme.colors
    spacing = theme.spacing
    return f"""
MessageComposerWidget {{
    background-color: {colors.composer_bg};
    border-top: 1px solid {colors.border_subtle};
}}
MessageComposerWidget QPlainTextEdit {{
    background-color: {colors.chat_bg};
    color: {colors.chat_text};
    border: 1px solid {colors.border_subtle};
    border-radius: 6px;
    padding: {spacing.sm}px;
}}
MessageComposerWidget QPushButton {{
    background-color: {colors.accent};
    color: #ffffff;
    border-radius: 6px;
    padding: {spacing.xs}px {spacing.md}px;
}}
MessageComposerWidget QPushButton:disabled {{
    background-color: {colors.border_subtle};
    color: {colors.sidebar_text};
}}
"""


def build_main_container_styles(theme: ThemeTokens) -> str:
    """Build stylesheet for MainLayoutContainer sidebar/chat surfaces."""
    colors = theme.colors
    return f"""
#sidebarPane {{
    background-color: {colors.sidebar_bg};
    color: {colors.sidebar_text};
}}
#chatPane {{
    background-color: {colors.chat_bg};
    color: {colors.chat_text};
}}
QSplitter::handle {{
    background-color: {colors.border_subtle};
}}
"""

