from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from win_llm_chat_pyside.features.attachments.attachments import (
    AttachmentExtractionError,
    AttachmentManager,
    FileTextExtractor,
    ExtractionResult,
)
from win_llm_chat_pyside.features.sessions.session_manager import SessionManager
from win_llm_chat_pyside.features.sessions.session_repository import SessionRepository


def _create_session_manager(tmp_path: Path) -> SessionManager:
    repo = SessionRepository(tmp_path / "sessions")
    manager = SessionManager(repository=repo)
    manager.initialize()
    return manager


@dataclass
class DummyExtractor:
    text: str
    page_count: int | None = None

    def extract_text(self, path: Path) -> ExtractionResult:  # noqa: ARG002
        return ExtractionResult(text=self.text, page_count=self.page_count)


class ErrorExtractor:
    def extract_text(self, path: Path) -> ExtractionResult:  # noqa: ARG002
        raise AttachmentExtractionError("failed to extract")


def test_attachment_manager_adds_and_extracts_text(tmp_path: Path):
    manager = _create_session_manager(tmp_path)
    session_id = manager.get_active_session_id()
    assert session_id is not None

    extractor = DummyExtractor(text="hello world", page_count=2)
    attachment_manager = AttachmentManager(
        session_manager=manager,
        text_extractor=extractor,
        max_text_length=5,
    )

    file_path = tmp_path / "doc.txt"
    file_path.write_text("source file", encoding="utf-8")

    metadata = attachment_manager.add_attachment(session_id, file_path)

    assert metadata.status == "ready"
    assert metadata.page_count == 2
    assert metadata.length_warning is True

    reloaded = manager.load_session(session_id)
    assert reloaded.attachments
    assert reloaded.attachments[0].filename == "doc.txt"
    stored_text = reloaded.attachment_texts.get(metadata.id)
    assert stored_text == "hello world"


def test_attachment_manager_marks_failure_when_extraction_fails(tmp_path: Path):
    manager = _create_session_manager(tmp_path)
    session_id = manager.get_active_session_id()
    assert session_id is not None

    attachment_manager = AttachmentManager(
        session_manager=manager,
        text_extractor=ErrorExtractor(),
    )

    file_path = tmp_path / "doc.md"
    file_path.write_text("content", encoding="utf-8")

    metadata = attachment_manager.add_attachment(session_id, file_path)

    assert metadata.status == "failed"
    assert metadata.error_message
    reloaded = manager.load_session(session_id)
    assert reloaded.attachments[0].status == "failed"
    assert metadata.id not in reloaded.attachment_texts


def test_attachment_manager_allows_skip_text_extraction(tmp_path: Path):
    manager = _create_session_manager(tmp_path)
    session_id = manager.get_active_session_id()
    assert session_id
    attachment_manager = AttachmentManager(
        session_manager=manager,
        text_extractor=ErrorExtractor(),
    )
    file_path = tmp_path / "image.png"
    file_path.write_bytes(b"\x89PNG")

    metadata = attachment_manager.add_attachment(
        session_id,
        file_path,
        source="clipboard_image",
        stored_file_path=str(file_path),
        skip_text_extraction=True,
    )

    assert metadata.status == "ready"
    assert metadata.source == "clipboard_image"


def test_attachment_manager_removes_stored_file(tmp_path: Path):
    manager = _create_session_manager(tmp_path)
    session_id = manager.get_active_session_id()
    assert session_id
    attachment_manager = AttachmentManager(session_manager=manager)

    stored_file = tmp_path / "persisted" / "img.png"
    stored_file.parent.mkdir(exist_ok=True, parents=True)
    stored_file.write_bytes(b"\x00\x01")

    metadata = attachment_manager.add_attachment(
        session_id,
        stored_file,
        source="clipboard_image",
        stored_file_path=str(stored_file),
        skip_text_extraction=True,
    )

    attachment_manager.remove_attachment(session_id, metadata.id)
    assert not stored_file.exists()


def test_file_text_extractor_reads_text_file(tmp_path: Path):
    file_path = tmp_path / "note.txt"
    file_path.write_text("こんにちは", encoding="utf-8")

    extractor = FileTextExtractor()
    result = extractor.extract_text(file_path)

    assert result.text == "こんにちは"
    assert result.page_count is None


def test_file_text_extractor_reads_pdf(monkeypatch, tmp_path: Path):
    file_path = tmp_path / "doc.pdf"
    file_path.write_bytes(b"%PDF-1.4 test content")

    class DummyPage:
        def extract_text(self) -> str:
            return "PDF body"

    class DummyReader:
        def __init__(self, path: Path):  # noqa: ARG002
            self.pages = [DummyPage()]

    monkeypatch.setattr(
        "win_llm_chat_pyside.features.attachments.attachments.PdfReader",
        DummyReader,
    )

    extractor = FileTextExtractor()
    result = extractor.extract_text(file_path)

    assert result.text == "PDF body"
    assert result.page_count == 1


def test_file_text_extractor_rejects_unknown_extension(tmp_path: Path):
    file_path = tmp_path / "data.bin"
    file_path.write_bytes(b"\x00\x01")

    extractor = FileTextExtractor()
    with pytest.raises(AttachmentExtractionError):
        extractor.extract_text(file_path)


