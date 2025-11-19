"""
Utilities for working with clipboard-provided images.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QGuiApplication, QImage


@dataclass
class ClipboardImageResult:
    """Successful clipboard capture."""

    image: QImage
    data: bytes
    mime_type: str
    size_bytes: int
    width: int
    height: int
    captured_at: datetime


@dataclass
class ClipboardImageError:
    """Clipboard capture error metadata."""

    code: str
    message: str


class ClipboardImageService:
    """Extracts and validates images from the OS clipboard."""

    def __init__(
        self,
        *,
        max_bytes: int = 2_000_000,
        max_total_pixels: int = 8_000_000,
        clipboard_provider: Callable[[], QImage | None] | None = None,
    ) -> None:
        self._max_bytes = max_bytes
        self._max_total_pixels = max_total_pixels
        self._clipboard_provider = clipboard_provider or self._default_clipboard_provider

    def capture_image(self) -> tuple[ClipboardImageResult | None, ClipboardImageError | None]:
        """
        Try to capture an image from the clipboard.

        Returns:
            (result, error)
        """

        image = self._clipboard_provider()
        if image is None or image.isNull():
            return None, None

        total_pixels = image.width() * image.height()
        if self._max_total_pixels > 0 and total_pixels > self._max_total_pixels:
            return None, ClipboardImageError(
                code="pixel_limit",
                message="クリップボード画像が大きすぎます。解像度を下げてから再度お試しください。",
            )

        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        # PNG に統一して保存し、ミームサイズを算出する
        if not image.save(buffer, "PNG"):
            return None, ClipboardImageError(
                code="encode_failed",
                message="クリップボード画像の取得に失敗しました。",
            )
        data = bytes(buffer.data())
        size_bytes = len(data)

        if self._max_bytes > 0 and size_bytes > self._max_bytes:
            return None, ClipboardImageError(
                code="byte_limit",
                message="クリップボード画像のサイズが上限を超えています。",
            )

        return (
            ClipboardImageResult(
                image=image,
                data=data,
                mime_type="image/png",
                size_bytes=size_bytes,
                width=image.width(),
                height=image.height(),
                captured_at=datetime.now(timezone.utc),
            ),
            None,
        )

    def _default_clipboard_provider(self) -> QImage | None:
        app = QGuiApplication.instance()
        if not app:
            return None
        clipboard = app.clipboard()
        if not clipboard or not clipboard.mimeData().hasImage():
            return None
        image = clipboard.image()
        if image.isNull():
            return None
        return image


def persist_clipboard_image(
    result: ClipboardImageResult,
    target_dir: Path,
    *,
    filename_prefix: str = "clipboard",
) -> Path:
    """
    Persist clipboard image bytes to disk and return the path.
    """

    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = result.captured_at.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"{filename_prefix}-{timestamp}-{uuid4().hex[:6]}.png"
    path = target_dir / filename
    with open(path, "wb") as fp:
        fp.write(result.data)
    return path


