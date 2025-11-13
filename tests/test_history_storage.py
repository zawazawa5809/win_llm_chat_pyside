import json
from pathlib import Path
import tempfile

from src.win_llm_chat_pyside.models import Message
from src.win_llm_chat_pyside import storage


def test_save_session_atomic_creates_file_and_backup():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "session.json"
        # 既存ファイルを作成
        p.write_text(json.dumps([{"role": "user", "content": "old"}], ensure_ascii=False, indent=2), encoding="utf-8")
        # 新しい内容を保存
        messages = [Message(role="user", content="hello"), Message(role="assistant", content="world")]
        storage.save_session_atomic(messages, p)
        # .bak があること
        assert (Path(td) / "session.json.bak").exists()
        # 内容が更新されていること
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data[0]["content"] == "hello"
        assert data[1]["role"] == "assistant"


def test_load_session_safe_invalid_json_raises():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "broken.json"
        p.write_text("{ invalid json", encoding="utf-8")
        try:
            storage.load_session_safe(p)
            assert False, "JSONDecodeError expected"
        except json.JSONDecodeError:
            pass


def test_render_markdown_contains_meta_and_roles():
    msgs = [Message(role="user", content="A"), Message(role="assistant", content="B")]
    md = storage.render_markdown(msgs, metadata={"model": "test-model"})
    assert "**User:**" in md
    assert "**Assistant:**" in md
    assert "model: test-model" in md


def test_calculate_history_size_counts_messages_and_chars():
    msgs = [Message(role="user", content="123"), Message(role="assistant", content="45")]
    num, chars = storage.calculate_history_size(msgs)
    assert num == 2
    assert chars == 5


