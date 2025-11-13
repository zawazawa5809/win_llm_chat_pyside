"""
iter_chat のストリーミング（OpenAI互換のSSE風、OllamaのJSON Lines）を単体テストする。
"""

import sys
from pathlib import Path
from typing import Iterable, List
from unittest.mock import patch

import pytest

# src/ をパスに追加（パッケージ import 用）
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from win_llm_chat_pyside.client import OpenAiCompatibleClient, OllamaClient  # noqa: E402
from win_llm_chat_pyside.models import Message  # noqa: E402


class MockStreamResponse:
    def __init__(self, lines: Iterable[str | bytes], status_code: int = 200, text: str = ""):
        self._lines: List[bytes] = [
            ln if isinstance(ln, bytes) else ln.encode("utf-8") for ln in lines
        ]
        self.status_code = status_code
        self.text = text
        self.encoding = None

    def iter_lines(self, decode_unicode: bool = False):
        for ln in self._lines:
            yield ln


class TestStreamingOpenAI:
    def test_iter_chat_sse_yields_deltas_and_stops_on_done(self):
        client = OpenAiCompatibleClient(base_url="http://dummy", model="gpt-x")
        msgs = [Message(role="user", content="Hello")]  # minimal content

        # SSE: "data: {...}" 行が複数、その後に "[DONE]"
        sse_lines = [
            "data: {\"choices\":[{\"delta\":{\"content\":\"や\"}}]}",
            "data: {\"choices\":[{\"delta\":{\"content\":\"っ\"}}]}",
            "data: {\"choices\":[{\"delta\":{\"content\":\"ほ\"}}]}",
            "data: [DONE]",
        ]
        with patch("requests.post", return_value=MockStreamResponse(sse_lines, 200)):
            chunks = list(client.iter_chat(msgs))
        assert "".join(chunks) == "やっほ"

    def test_iter_chat_sse_ignores_non_data_and_bad_json(self):
        client = OpenAiCompatibleClient(base_url="http://dummy", model="gpt-x")
        msgs = [Message(role="user", content="Hi")]
        sse_lines = [
            ": ping",  # コメント行想定 → 無視される
            "data: this-is-not-json",  # 破損 → スキップ
            "data: {\"choices\":[{\"delta\":{\"content\":\"A\"}}]}",
            "data: [DONE]",
        ]
        with patch("requests.post", return_value=MockStreamResponse(sse_lines, 200)):
            chunks = list(client.iter_chat(msgs))
        assert "".join(chunks) == "A"


class TestStreamingOllama:
    def test_iter_chat_jsonl_yields_until_done_true(self):
        client = OllamaClient(base_url="http://dummy", model="llama3")
        msgs = [Message(role="user", content="Hello")]
        jsonl_lines = [
            '{"message":{"role":"assistant","content":"こ"},"done":false}',
            '{"message":{"role":"assistant","content":"ん"},"done":false}',
            '{"message":{"role":"assistant","content":"に"},"done":false}',
            '{"done":true}',
        ]
        with patch("requests.post", return_value=MockStreamResponse(jsonl_lines, 200)):
            chunks = list(client.iter_chat(msgs))
        assert "".join(chunks) == "こんに"

    def test_iter_chat_jsonl_skips_invalid_frames(self):
        client = OllamaClient(base_url="http://dummy", model="llama3")
        msgs = [Message(role="user", content="Hello")]
        jsonl_lines = [
            'this-is-not-json',
            '{"message":{"role":"assistant","content":"X"},"done":false}',
            '{"done":true}',
        ]
        with patch("requests.post", return_value=MockStreamResponse(jsonl_lines, 200)):
            chunks = list(client.iter_chat(msgs))
        assert "".join(chunks) == "X"


