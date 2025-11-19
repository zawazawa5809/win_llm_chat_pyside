from pathlib import Path
import tempfile

from win_llm_chat_pyside.models import AttachmentMetadata, Message, Session
from win_llm_chat_pyside.features.sessions.session_repository import SessionRepository


def _sample_session(session_id: str = "sess-1") -> Session:
    return Session(
        id=session_id,
        name="テストセッション",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        messages=[Message(role="user", content="hello"), Message(role="assistant", content="world")],
    )


def test_session_repository_save_and_load_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        repo = SessionRepository(Path(td))
        session = _sample_session()
        repo.save_session(session)
        repo.save_index([session.to_meta()])

        loaded_index = repo.load_index()
        assert len(loaded_index) == 1
        assert loaded_index[0].name == "テストセッション"

        loaded_session = repo.load_session(session.id)
        assert len(loaded_session.messages) == 2
        assert loaded_session.messages[0].content == "hello"


def test_session_repository_delete_session():
    with tempfile.TemporaryDirectory() as td:
        repo = SessionRepository(Path(td))
        session = _sample_session("sess-del")
        repo.save_session(session)
        repo.delete_session(session.id)
        try:
            repo.load_session(session.id)
            assert False, "File should be deleted"
        except FileNotFoundError:
            pass


def test_session_repository_persists_attachments():
    with tempfile.TemporaryDirectory() as td:
        repo = SessionRepository(Path(td))
        session = _sample_session("sess-attachments")
        attachment = AttachmentMetadata(
            id="att-1",
            session_id=session.id,
            filename="doc.pdf",
            size_bytes=1024,
            mime_type="application/pdf",
            page_count=3,
            text_length=500,
            status="ready",
            error_message=None,
            length_warning=True,
        )
        session.attachments = [attachment]
        session.attachment_texts = {attachment.id: "extracted text"}

        repo.save_session(session)
        loaded = repo.load_session(session.id)

        assert loaded.attachments
        loaded_attachment = loaded.attachments[0]
        assert loaded_attachment.filename == "doc.pdf"
        assert loaded_attachment.status == "ready"
        assert loaded_attachment.length_warning is True
        assert loaded.attachment_texts[attachment.id] == "extracted text"


