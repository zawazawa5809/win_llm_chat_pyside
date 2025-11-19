"""
SessionManager: セッション一覧とアクティブセッションを管理する。
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from win_llm_chat_pyside.services import storage
from win_llm_chat_pyside.models import Message, Session, SessionMeta, SessionSummary
from win_llm_chat_pyside.features.sessions.session_repository import SessionRepository


class SessionManager:
    """SessionRepository を用いてセッションの CRUD と移行を担う。"""

    def __init__(
        self,
        repository: SessionRepository,
        legacy_path: Optional[Path] = None,
        persist: bool = True,
    ):
        self._repo = repository
        self._legacy_path = legacy_path
        self._persist = persist
        self._metas: List[SessionMeta] = []
        self._session_cache: Dict[str, Session] = {}
        self._active_session_id: Optional[str] = None

    def initialize(self) -> List[SessionMeta]:
        """インデックスをロードし、必要に応じてブートストラップする。"""
        self._metas = self._repo.load_index()
        if not self._metas:
            self._metas = self._bootstrap_sessions()
        if self._metas and not self._active_session_id:
            self._active_session_id = self._metas[0].id
        return list(self._metas)

    def list_sessions(self) -> List[SessionMeta]:
        return list(self._metas)

    def get_active_session_id(self) -> Optional[str]:
        return self._active_session_id

    def set_active_session(self, session_id: str) -> None:
        if not any(meta.id == session_id for meta in self._metas):
            raise KeyError(f"session not found: {session_id}")
        self._active_session_id = session_id

    def load_session(self, session_id: str) -> Session:
        session = self._session_cache.get(session_id)
        if session is None or self._persist:
            # 常に最新を読み込む。persist=False 時はキャッシュを利用。
            if self._persist:
                session = self._repo.load_session(session_id)
            else:
                session = self._session_cache.get(session_id)
        if session is None:
            # persist=False かつキャッシュ無しの場合は空セッションを生成
            session = self._create_session_object(session_id, "新規セッション", [])
            self._session_cache[session_id] = session
        else:
            self._session_cache[session_id] = session
        return session

    def create_session(
        self,
        name: Optional[str] = None,
        role_profile_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> Session:
        session = self._create_session_object(
            self._generate_id(),
            name,
            [],
            role_profile_id=role_profile_id,
            system_prompt=system_prompt,
        )
        self._session_cache[session.id] = session
        self._metas.insert(0, session.to_meta())
        self._save_session(session)
        self._save_index()
        self._active_session_id = session.id
        return session

    def rename_session(self, session_id: str, new_name: str) -> SessionMeta:
        session = self._ensure_session_loaded(session_id)
        session.name = new_name
        session.updated_at = self._now()
        self._update_meta(session)
        self._save_session(session)
        self._save_index()
        return session.to_meta()

    def delete_session(self, session_id: str) -> Optional[str]:
        if len(self._metas) <= 1:
            raise ValueError("少なくとも1つのセッションが必要です")
        self._metas = [m for m in self._metas if m.id != session_id]
        self._session_cache.pop(session_id, None)
        if self._persist:
            self._repo.delete_session(session_id)
        if self._active_session_id == session_id:
            self._active_session_id = self._metas[0].id if self._metas else None
        self._save_index()
        if not self._metas:
            new_session = self.create_session()
            return new_session.id
        return self._active_session_id

    def save_session_messages(self, session_id: str, messages: List[Message]) -> None:
        session = self._ensure_session_loaded(session_id)
        session.messages = [Message(role=m.role, content=m.content) for m in messages]
        session.updated_at = self._now()
        self._update_meta(session)
        self._save_session(session)
        self._save_index()

    def update_session(self, session: Session) -> None:
        """セッション全体の更新を保存する。"""
        session.updated_at = self._now()
        self._session_cache[session.id] = session
        self._update_meta(session)
        self._save_session(session)
        self._save_index()

    # ---- internal helpers ----
    def _bootstrap_sessions(self) -> List[SessionMeta]:
        migrated = self._try_migrate_from_legacy()
        if migrated:
            return migrated
        session = self._create_session_object(self._generate_id(), None, [])
        self._session_cache[session.id] = session
        if self._persist:
            self._repo.save_session(session)
            self._repo.save_index([session.to_meta()])
        return [session.to_meta()]

    def _try_migrate_from_legacy(self) -> List[SessionMeta]:
        if not self._legacy_path or not self._legacy_path.exists():
            return []
        try:
            messages = storage.load_session_safe(self._legacy_path)
        except Exception:
            return []
        session = self._create_session_object(
            self._generate_id(),
            "インポートされたセッション",
            messages,
        )
        self._session_cache[session.id] = session
        if self._persist:
            self._repo.save_session(session)
            self._repo.save_index([session.to_meta()])
        return [session.to_meta()]

    def _create_session_object(
        self,
        session_id: str,
        name: Optional[str],
        messages: List[Message],
        *,
        role_profile_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> Session:
        now = self._now()
        resolved_name = name.strip() if name else self._generate_default_name()
        normalized_messages = [Message(role=m.role, content=m.content) for m in messages]
        if system_prompt:
            normalized_messages.insert(0, Message(role="system", content=system_prompt))
        return Session(
            id=session_id,
            name=resolved_name,
            created_at=now,
            updated_at=now,
            messages=normalized_messages,
            role_profile_id=role_profile_id,
        )

    def _generate_default_name(self) -> str:
        base = "新規セッション"
        existing = {meta.name for meta in self._metas}
        if base not in existing:
            return base
        idx = 2
        while f"{base} {idx}" in existing:
            idx += 1
        return f"{base} {idx}"

    def _ensure_session_loaded(self, session_id: str) -> Session:
        session = self._session_cache.get(session_id)
        if session:
            return session
        session = self._repo.load_session(session_id)
        self._session_cache[session_id] = session
        return session

    def _update_meta(self, session: Session) -> None:
        updated_meta = session.to_meta()
        for idx, meta in enumerate(self._metas):
            if meta.id == session.id:
                self._metas[idx] = updated_meta
                break

    def _save_session(self, session: Session) -> None:
        if self._persist:
            self._repo.save_session(session)

    def _save_index(self) -> None:
        if self._persist:
            self._repo.save_index(self._metas)

    def _generate_id(self) -> str:
        return uuid.uuid4().hex

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    # ---- role profile handling ----
    def apply_role_profile(
        self,
        session_id: str,
        role_profile_id: Optional[str],
        system_prompt: Optional[str],
    ) -> Session:
        session = self._ensure_session_loaded(session_id)
        session.role_profile_id = role_profile_id
        if system_prompt:
            session.messages.append(Message(role="system", content=system_prompt))
        session.updated_at = self._now()
        self._update_meta(session)
        self._save_session(session)
        self._save_index()
        return session

    # ---- summaries ----
    def build_session_summaries(
        self,
        *,
        max_messages: int = 5,
        max_chars_per_message: int = 500,
    ) -> List[SessionSummary]:
        """セッション名＋冒頭メッセージのプレーンテキストを返す。"""
        summaries: list[SessionSummary] = []
        for meta in self._metas:
            try:
                session = self.load_session(meta.id)
            except Exception:
                continue
            preview_parts: list[str] = []
            for message in session.messages[: max(1, max_messages)]:
                content = (message.content or "").strip()
                if not content:
                    continue
                snippet = content.replace("\r\n", "\n").replace("\r", "\n")
                snippet_lines = snippet.split("\n")
                normalized = " ".join(part.strip() for part in snippet_lines if part.strip())
                if not normalized:
                    continue
                preview_parts.append(normalized[: max(1, max_chars_per_message)])
            preview_text = "\n".join(preview_parts)
            summaries.append(
                SessionSummary(
                    id=meta.id,
                    name=meta.name,
                    updated_at=meta.updated_at,
                    preview_text=preview_text,
                )
            )
        return summaries



