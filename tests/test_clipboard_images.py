from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from win_llm_chat_pyside.services.clipboard import ClipboardImageService, persist_clipboard_image


def _sample_image() -> QImage:
    image = QImage(8, 8, QImage.Format_RGBA8888)
    image.fill(Qt.white)
    return image


def test_clipboard_service_returns_none_when_no_image():
    service = ClipboardImageService(clipboard_provider=lambda: None)
    result, error = service.capture_image()
    assert result is None
    assert error is None


def test_clipboard_service_enforces_byte_limit():
    image = _sample_image()
    service = ClipboardImageService(max_bytes=1, clipboard_provider=lambda: image)
    result, error = service.capture_image()
    assert result is None
    assert error
    assert error.code == "byte_limit"


def test_clipboard_service_persists_image(tmp_path, qt_app):  # noqa: ARG001
    image = _sample_image()
    service = ClipboardImageService(clipboard_provider=lambda: image)
    result, error = service.capture_image()
    assert error is None
    assert result is not None

    path = persist_clipboard_image(result, tmp_path)
    assert path.exists()
    assert path.read_bytes()

