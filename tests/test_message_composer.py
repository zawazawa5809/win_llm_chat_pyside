from datetime import datetime, timezone

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent, QImage

from win_llm_chat_pyside.services.clipboard import ClipboardImageResult
from win_llm_chat_pyside.models.layout_mode import LayoutMode
from win_llm_chat_pyside.features.chat.message_composer import MessageComposerWidget


def test_default_mode_is_focused(qt_app):
    widget = MessageComposerWidget()

    assert widget.layout_mode is LayoutMode.FOCUSED
    assert widget.template_bar.isHidden() is False
    assert widget.input_field.maximumHeight() == widget.FOCUSED_MAX_INPUT_HEIGHT


def test_compact_mode_hides_template_bar_and_limits_height(qt_app):
    widget = MessageComposerWidget()

    widget.set_layout_mode(LayoutMode.COMPACT)

    assert widget.template_bar.isHidden() is True
    assert widget.input_field.maximumHeight() == widget.COMPACT_MAX_INPUT_HEIGHT


def test_switching_back_to_focused_restores_template_bar(qt_app):
    widget = MessageComposerWidget()
    widget.set_layout_mode(LayoutMode.COMPACT)

    widget.set_layout_mode(LayoutMode.FOCUSED)

    assert widget.template_bar.isHidden() is False
    assert widget.input_field.maximumHeight() == widget.FOCUSED_MAX_INPUT_HEIGHT


def test_message_composer_applies_theme_colors(qt_app):
    widget = MessageComposerWidget()
    style = widget.styleSheet()

    assert "background-color" in style


def test_message_composer_send_button_click_emits_signal(qt_app):
    widget = MessageComposerWidget()
    triggered = []

    def track():
        triggered.append(True)

    widget.send_button.clicked.connect(track)
    widget.send_button.click()

    assert triggered


def test_configure_send_shortcuts_handles_enter_to_send(qt_app):
    widget = MessageComposerWidget()
    widget.configure_send_shortcuts(enter_to_send=True, ctrl_enter_to_send=False)
    triggered: list[bool] = []
    widget.send_requested.connect(lambda: triggered.append(True))

    event = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier)
    qt_app.sendEvent(widget.input_field, event)

    assert triggered


def test_configure_send_shortcuts_handles_ctrl_enter_only(qt_app):
    widget = MessageComposerWidget()
    widget.configure_send_shortcuts(enter_to_send=False, ctrl_enter_to_send=True)
    triggered: list[bool] = []
    widget.send_requested.connect(lambda: triggered.append(True))

    ctrl_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.ControlModifier)
    qt_app.sendEvent(widget.input_field, ctrl_event)
    assert triggered

    triggered.clear()
    enter_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier)
    qt_app.sendEvent(widget.input_field, enter_event)
    assert not triggered


class _StubClipboardService:
    def __init__(self, result: ClipboardImageResult | None, error=None):
        self._result = result
        self._error = error

    def capture_image(self):
        return self._result, self._error


def _build_clipboard_result() -> ClipboardImageResult:
    image = QImage(10, 10, QImage.Format_RGBA8888)
    image.fill(Qt.white)
    return ClipboardImageResult(
        image=image,
        data=b"\x89PNG",
        mime_type="image/png",
        size_bytes=4,
        width=10,
        height=10,
        captured_at=datetime.now(timezone.utc),
    )


def test_message_composer_queues_clipboard_image(qt_app):
    widget = MessageComposerWidget()
    result = _build_clipboard_result()
    widget.set_clipboard_image_service(_StubClipboardService(result))

    event = QKeyEvent(QEvent.KeyPress, Qt.Key_V, Qt.ControlModifier)
    qt_app.sendEvent(widget.input_field, event)

    pending = widget.pending_clipboard_images()
    assert len(pending) == 1
    widget.clear_clipboard_images()
    assert widget.pending_clipboard_images() == []


def test_message_composer_allows_text_paste_when_input_not_empty(qt_app):
    widget = MessageComposerWidget()
    result = _build_clipboard_result()
    widget.set_clipboard_image_service(_StubClipboardService(result))
    widget.input_field.setPlainText("hello")

    event = QKeyEvent(QEvent.KeyPress, Qt.Key_V, Qt.ControlModifier)
    qt_app.sendEvent(widget.input_field, event)

    assert widget.pending_clipboard_images() == []


