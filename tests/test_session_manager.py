from pathlib import Path
import tempfile

from src.win_llm_chat_pyside import storage
from src.win_llm_chat_pyside.models import Message
from src.win_llm_chat_pyside.session_manager import SessionManager
from src.win_llm_chat_pyside.session_repository import SessionRepository


def _create_manager(tmp_dir: Path, persist: bool = True, legacy_file: Path | None = None) -> SessionManager:
    repo = SessionRepository(tmp_dir / "sessions")
    legacy = legacy_file
    return SessionManager(repository=repo, legacy_path=legacy, persist=persist)


def test_session_manager_bootstrap_creates_default_session():
    with tempfile.TemporaryDirectory() as td:
        manager = _create_manager(Path(td))
        metas = manager.initialize()
        assert len(metas) == 1
        active_id = manager.get_active_session_id()
        assert active_id == metas[0].id
        session = manager.load_session(active_id)
        assert session.messages == []


def test_session_manager_create_rename_and_save_messages():
    with tempfile.TemporaryDirectory() as td:
        manager = _create_manager(Path(td))
        manager.initialize()
        new_session = manager.create_session("案件A")
        assert new_session.name == "案件A"
        manager.rename_session(new_session.id, "案件A-更新")
        metas = manager.list_sessions()
        assert any(meta.name == "案件A-更新" for meta in metas)
        messages = [Message(role="user", content="hello"), Message(role="assistant", content="world")]
        manager.save_session_messages(new_session.id, messages)
        reloaded = manager.load_session(new_session.id)
        assert len(reloaded.messages) == 2
        assert reloaded.messages[1].content == "world"


def test_session_manager_migrates_from_legacy_json():
    with tempfile.TemporaryDirectory() as td:
        legacy_path = Path(td) / "session.json"
        storage.save_session_atomic([Message(role="user", content="legacy")], legacy_path)
        manager = _create_manager(Path(td), legacy_file=legacy_path)
        metas = manager.initialize()
        assert len(metas) == 1
        session = manager.load_session(metas[0].id)
        assert session.messages[0].content == "legacy"


