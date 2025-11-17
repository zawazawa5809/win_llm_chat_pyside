"""Message composer widget that consolidates template and input controls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from PySide6.QtCore import Qt, QEvent, QSize, Signal
from PySide6.QtGui import QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .clipboard_images import ClipboardImageResult, ClipboardImageService
from .layout_mode import LayoutMode
from .theme import build_composer_styles, get_theme


@dataclass
class PendingClipboardImage:
    """Client-side clipboard image awaiting persistence."""

    id: str
    display_name: str
    captured_at: datetime
    data: bytes
    mime_type: str
    size_bytes: int
    width: int
    height: int
    pixmap: QPixmap


class MessageComposerWidget(QWidget):
    """Provides the chat input area with template controls."""

    FOCUSED_MAX_INPUT_HEIGHT = 140
    COMPACT_MAX_INPUT_HEIGHT = 60

    send_requested = Signal()
    clipboard_image_error = Signal(str)
    clipboard_image_added = Signal(int)
    clipboard_image_removed = Signal()

    def __init__(self, parent: QWidget | None = None, *, theme=None) -> None:
        super().__init__(parent)
        self._layout_mode: LayoutMode = LayoutMode.FOCUSED
        self._theme = theme or get_theme()
        self._enter_to_send = False
        self._ctrl_enter_to_send = True
        self._clipboard_service: ClipboardImageService | None = None
        self._pending_images: list[PendingClipboardImage] = []
        self._preview_widgets: dict[str, _ClipboardPreviewChip] = {}
        self._build_ui()
        self._apply_theme_styles()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Template bar（テンプレ挿入だけを扱う）
        self.template_bar = QWidget(self)
        template_layout = QHBoxLayout(self.template_bar)
        template_layout.setContentsMargins(0, 0, 0, 0)
        template_layout.setSpacing(8)
        self.template_combo = QComboBox(self.template_bar)
        self.template_combo.setEditable(False)
        self.template_combo.setPlaceholderText("テンプレートを選択...")
        self.template_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.template_insert_button = QPushButton("挿入", self.template_bar)
        template_layout.addWidget(self.template_combo, stretch=1)
        template_layout.addWidget(self.template_insert_button, stretch=0)
        layout.addWidget(self.template_bar)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self.input_field = QPlainTextEdit(self)
        self.input_field.setPlaceholderText("メッセージを入力...")
        self.input_field.setMaximumHeight(self.FOCUSED_MAX_INPUT_HEIGHT)
        self.input_field.installEventFilter(self)
        input_row.addWidget(self.input_field, stretch=4)

        self.send_button = QPushButton("送信", self)
        input_row.addWidget(self.send_button, stretch=0)

        self.stop_button = QPushButton("停止", self)
        self.stop_button.setEnabled(False)
        input_row.addWidget(self.stop_button, stretch=0)

        layout.addLayout(input_row)

        self.clipboard_preview = QFrame(self)
        self.clipboard_preview.setObjectName("clipboardPreview")
        preview_wrapper = QVBoxLayout(self.clipboard_preview)
        preview_wrapper.setContentsMargins(4, 4, 4, 4)
        preview_wrapper.setSpacing(4)
        self.clipboard_preview_label = QLabel("貼り付けた画像", self.clipboard_preview)
        self.clipboard_preview_label.setObjectName("clipboardPreviewLabel")
        preview_wrapper.addWidget(self.clipboard_preview_label, alignment=Qt.AlignLeft)
        self._attachment_preview_layout = QHBoxLayout()
        self._attachment_preview_layout.setContentsMargins(0, 0, 0, 0)
        self._attachment_preview_layout.setSpacing(8)
        preview_wrapper.addLayout(self._attachment_preview_layout)
        layout.addWidget(self.clipboard_preview)
        self.clipboard_preview.setVisible(False)

    @property
    def layout_mode(self) -> LayoutMode:
        return self._layout_mode

    def set_layout_mode(self, mode: LayoutMode) -> None:
        if mode == self._layout_mode:
            return
        self._layout_mode = mode
        if mode is LayoutMode.COMPACT:
            self.template_bar.setVisible(False)
            self.input_field.setMaximumHeight(self.COMPACT_MAX_INPUT_HEIGHT)
        else:
            self.template_bar.setVisible(True)
            self.input_field.setMaximumHeight(self.FOCUSED_MAX_INPUT_HEIGHT)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(build_composer_styles(self._theme))

    def configure_send_shortcuts(self, *, enter_to_send: bool, ctrl_enter_to_send: bool) -> None:
        self._enter_to_send = enter_to_send
        self._ctrl_enter_to_send = ctrl_enter_to_send

    def focus_input_field(self) -> None:
        self.input_field.setFocus()
        cursor = self.input_field.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.input_field.setTextCursor(cursor)

    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self.input_field and event.type() == QEvent.KeyPress:
            key_event = event  # type: ignore[assignment]
            key = key_event.key()
            mods = key_event.modifiers()
            if key == Qt.Key_V and mods & Qt.ControlModifier:
                if self._handle_clipboard_paste():
                    return True
            if (mods & Qt.ShiftModifier) and key in (Qt.Key_Return, Qt.Key_Enter):
                return False
            if self._ctrl_enter_to_send and (mods & Qt.ControlModifier) and key in (Qt.Key_Return, Qt.Key_Enter):
                self.send_requested.emit()
                return True
            if self._enter_to_send and mods == Qt.NoModifier and key in (Qt.Key_Return, Qt.Key_Enter):
                self.send_requested.emit()
                return True
        return super().eventFilter(obj, event)

    def set_clipboard_image_service(self, service: ClipboardImageService | None) -> None:
        self._clipboard_service = service

    def pending_clipboard_images(self) -> list[PendingClipboardImage]:
        return list(self._pending_images)

    def take_pending_clipboard_images(self) -> list[PendingClipboardImage]:
        images = list(self._pending_images)
        self.clear_clipboard_images()
        return images

    def clear_clipboard_images(self) -> None:
        self._pending_images.clear()
        for widget in self._preview_widgets.values():
            widget.deleteLater()
        self._preview_widgets.clear()
        self.clipboard_preview.setVisible(False)

    def _handle_clipboard_paste(self) -> bool:
        if not self._clipboard_service:
            return False
        result, error = self._clipboard_service.capture_image()
        if error:
            self.clipboard_image_error.emit(error.message)
            return True
        if result is None:
            return False
        if self._input_field_has_text():
            return False
        self._enqueue_clipboard_image(result)
        self.clipboard_image_added.emit(result.size_bytes)
        return True

    def _enqueue_clipboard_image(self, result: ClipboardImageResult) -> None:
        pixmap = QPixmap.fromImage(result.image).scaled(
            96,
            96,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        pending = PendingClipboardImage(
            id=uuid4().hex,
            display_name=self._build_clipboard_display_name(len(self._pending_images) + 1),
            captured_at=result.captured_at,
            data=result.data,
            mime_type=result.mime_type,
            size_bytes=result.size_bytes,
            width=result.width,
            height=result.height,
            pixmap=pixmap,
        )
        self._pending_images.append(pending)
        chip = _ClipboardPreviewChip(pending)
        chip.remove_requested.connect(self._remove_clipboard_image)
        self._attachment_preview_layout.addWidget(chip)
        self._preview_widgets[pending.id] = chip
        self.clipboard_preview.setVisible(True)

    def _remove_clipboard_image(self, image_id: str) -> None:
        self._pending_images = [img for img in self._pending_images if img.id != image_id]
        widget = self._preview_widgets.pop(image_id, None)
        if widget:
            widget.deleteLater()
        self.clipboard_image_removed.emit()
        if not self._pending_images:
            self.clipboard_preview.setVisible(False)

    def _build_clipboard_display_name(self, index: int) -> str:
        return f"スクリーンショット {index}"

    def _input_field_has_text(self) -> bool:
        return bool(self.input_field.toPlainText().strip())


class _ClipboardPreviewChip(QFrame):
    """Small preview widget for a queued clipboard image."""

    remove_requested = Signal(str)

    def __init__(self, pending: PendingClipboardImage) -> None:
        super().__init__()
        self._pending = pending
        self.setObjectName("clipboardPreviewChip")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        self._image_label = QLabel(self)
        self._image_label.setPixmap(pending.pixmap)
        self._image_label.setFixedSize(QSize(96, 96))
        self._image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._image_label)

        caption = QLabel(f"{pending.display_name}\n{pending.width}×{pending.height}", self)
        caption.setAlignment(Qt.AlignCenter)
        layout.addWidget(caption)

        remove_button = QToolButton(self)
        remove_button.setText("削除")
        remove_button.clicked.connect(self._emit_remove)
        layout.addWidget(remove_button)

        self.setFrameShape(QFrame.StyledPanel)

    def _emit_remove(self) -> None:
        self.remove_requested.emit(self._pending.id)

