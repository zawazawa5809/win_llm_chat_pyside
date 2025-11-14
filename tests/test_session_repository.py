from pathlib import Path
import tempfile

from src.win_llm_chat_pyside.models import Message, Session
from src.win_llm_chat_pyside.session_repository import SessionRepository


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


