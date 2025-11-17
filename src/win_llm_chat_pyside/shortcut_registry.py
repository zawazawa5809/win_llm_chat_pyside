"""Shortcut registry for aggregating in-app and global shortcuts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Scope = Literal["app", "global"]


@dataclass(frozen=True)
class ShortcutMeta:
    """Metadata describing a single shortcut entry."""

    key: str
    description: str
    category: str
    scope: Scope = "app"


class ShortcutRegistry:
    """Collects shortcut metadata for help views and diagnostics."""

    def __init__(self) -> None:
        self._entries: dict[str, ShortcutMeta] = {}

    def register(
        self,
        *,
        key: str,
        description: str,
        category: str,
        scope: Scope = "app",
    ) -> ShortcutMeta:
        """Register a shortcut. Raises ValueError on conflicting duplicates."""

        normalized_key = self._normalize_key(key)
        meta = ShortcutMeta(
            key=normalized_key,
            description=description.strip(),
            category=category.strip() or "その他",
            scope=scope,
        )
        existing = self._entries.get(normalized_key)
        if existing and existing != meta:
            raise ValueError(f"Shortcut '{normalized_key}' is already registered with '{existing.description}'.")
        self._entries[normalized_key] = meta
        return meta

    def unregister(self, key: str) -> None:
        """Remove a shortcut entry if present."""

        normalized_key = self._normalize_key(key)
        self._entries.pop(normalized_key, None)

    def all(self) -> list[ShortcutMeta]:
        """Return all registered shortcuts in insertion order."""

        return list(self._entries.values())

    @staticmethod
    def _normalize_key(key: str) -> str:
        normalized = (key or "").strip()
        if not normalized:
            raise ValueError("Shortcut key must not be empty.")
        return normalized


