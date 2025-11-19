"""
送信処理をバックグラウンドで実行する Worker 実装。
"""

from __future__ import annotations

from time import perf_counter
from typing import List, Optional
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from win_llm_chat_pyside.models import Message
from win_llm_chat_pyside.services.llm_client import (
    LlmClientError,
    AuthenticationError,
    NetworkError,
    ResponseFormatError,
)


class ChatWorker(QObject):
    """LLM 送信処理を別スレッドで実行するワーカー。"""

    succeeded = Signal(str, int)  # content, elapsed_ms
    failed = Signal(str, str, int)  # user_message, detail, elapsed_ms

    def __init__(self, client, messages: List[Message], llm_options: Optional[dict] = None):
        super().__init__()
        self._client = client
        self._messages = messages
        self._llm_options = llm_options or {}

    @Slot()
    def run(self) -> None:
        """送信処理を実行する。"""
        start = perf_counter()
        try:
            content = self._client.send_chat(self._messages, options=self._llm_options)
            elapsed_ms = int((perf_counter() - start) * 1000)
            self.succeeded.emit(content, elapsed_ms)
        except Exception as e:  # noqa: BLE001 - 型でメッセージ分岐したい
            elapsed_ms = int((perf_counter() - start) * 1000)
            user_message = self._map_error_to_user_message(e)
            self.failed.emit(user_message, repr(e), elapsed_ms)

    @staticmethod
    def _map_error_to_user_message(error: Exception) -> str:
        """例外をユーザー向けメッセージに変換する。"""
        if isinstance(error, AuthenticationError):
            return "認証に失敗しました（API キーを確認してください）"
        if isinstance(error, ResponseFormatError):
            return "不正な応答を受信しました"
        if isinstance(error, NetworkError):
            # NetworkError は接続失敗/HTTP/タイムアウトの可能性がある
            text = str(error)
            if "タイムアウト" in text or "timeout" in text.lower():
                return "応答がタイムアウトしました"
            if "HTTP エラー" in text or "status code" in text.lower():
                # 代表的なステータスのヒント
                if "401" in text or "403" in text:
                    return "認証に失敗しました（API キーを確認してください）"
                if "404" in text:
                    return "エンドポイントが見つかりません"
                if "429" in text:
                    return "リクエストが多すぎます（しばらく待ってから再試行）"
                if "5" in text:
                    return "サーバでエラーが発生しました"
                return "通信でエラーが発生しました"
            return "サーバに接続できません"
        if isinstance(error, LlmClientError):
            return "通信中にエラーが発生しました"
        return "予期しないエラーが発生しました"


class StreamChatWorker(QObject):
    """LLM ストリーミング処理を別スレッドで実行するワーカー。"""

    stream_chunk = Signal(str)  # delta text
    stream_finished = Signal(int)  # elapsed_ms
    failed = Signal(str, str, int)  # user_message, detail, elapsed_ms

    def __init__(self, client, messages: List[Message], llm_options: Optional[dict] = None):
        super().__init__()
        self._client = client
        self._messages = messages
        self._cancelled = False
        self._llm_options = llm_options or {}

    def cancel(self) -> None:
        """ストリーム処理の中断要求をセットする。"""
        self._cancelled = True

    def _map_error_to_user_message(self, error: Exception) -> str:
        # 既存のマッピングを再利用
        return ChatWorker._map_error_to_user_message(error)

    def run(self) -> None:
        """ストリーム処理を実行する。"""
        start = perf_counter()
        try:
            # iter_chat は非対応時に一括応答へフォールバックする実装
            for delta in self._client.iter_chat(self._messages, options=self._llm_options):
                if self._cancelled:
                    break
                if delta:
                    self.stream_chunk.emit(delta)
            elapsed_ms = int((perf_counter() - start) * 1000)
            self.stream_finished.emit(elapsed_ms)
        except Exception as e:  # noqa: BLE001
            elapsed_ms = int((perf_counter() - start) * 1000)
            user_message = self._map_error_to_user_message(e)
            self.failed.emit(user_message, repr(e), elapsed_ms)


class LoadSessionWorker(QObject):
    """セッション読み込みを別スレッドで実行するワーカー。"""

    succeeded = Signal(list)  # messages: List[Message]
    failed = Signal(str)  # detail

    def __init__(self, path: Path):
        super().__init__()
        self._path = path

    @Slot()
    def run(self) -> None:
        from win_llm_chat_pyside.services.storage import load_session_safe
        try:
            messages = load_session_safe(self._path)
            self.succeeded.emit(messages)  # type: ignore[arg-type]
        except Exception as e:  # noqa: BLE001
            self.failed.emit(repr(e))


class SaveSessionWorker(QObject):
    """セッション保存を別スレッドで実行するワーカー。"""

    succeeded = Signal()
    failed = Signal(str)  # detail

    def __init__(self, path: Path, messages: List[Message]):
        super().__init__()
        self._path = path
        self._messages = messages

    @Slot()
    def run(self) -> None:
        from win_llm_chat_pyside.services.storage import save_session_atomic
        try:
            save_session_atomic(self._messages, self._path)
            self.succeeded.emit()
        except Exception as e:  # noqa: BLE001
            self.failed.emit(repr(e))
