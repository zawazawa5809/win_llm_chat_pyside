"""
SessionRepository: セッションデータの永続化を担当する。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from .models import Session, SessionMeta

# 現在のフォーマットバージョン
SESSION_FORMAT_VERSION = "1.7"
INDEX_FORMAT_VERSION = "1.6"


class SessionRepository:
    """セッションメタと本体の JSON 永続化を扱う。"""

    def __init__(self, base_dir: Path):
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._base_dir / "index.json"

    def load_index(self) -> List[SessionMeta]:
        if not self._index_path.exists():
            return []
        with open(self._index_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # バージョンチェックとマイグレーション
        items_raw: list[dict] = []
        if isinstance(raw, dict) and "version" in raw:
            version = raw.get("version", "1.0")
            items_raw = raw.get("items") or raw.get("sessions") or []
            if version != INDEX_FORMAT_VERSION:
                # 将来のマイグレーション処理をここに追加
                pass
        elif isinstance(raw, list):
            # 旧フォーマット（配列のみ）: バージョンなし
            items_raw = raw
        items = [item for item in items_raw if isinstance(item, dict)]
        metas = [SessionMeta.from_dict(item) for item in items]
        # 読み込み時に最新フォーマットで保存し直す（マイグレーション）
        if isinstance(raw, list) or (isinstance(raw, dict) and raw.get("version") != INDEX_FORMAT_VERSION):
            self.save_index(metas)
        return metas

    def save_index(self, metas: List[SessionMeta]) -> None:
        data = {
            "version": INDEX_FORMAT_VERSION,
            "items": [meta.to_dict() for meta in metas],
        }
        self._write_json_atomic(self._index_path, data)

    def load_session(self, session_id: str) -> Session:
        path = self._session_path(session_id)
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # バージョンチェックとマイグレーション
        if isinstance(raw, dict):
            version = raw.get("version", "1.0")
            session_data = raw if "id" in raw else raw.get("session", raw)
            if version != SESSION_FORMAT_VERSION:
                # 将来のマイグレーション処理をここに追加
                pass
            session = Session.from_dict(session_data)
            # 読み込み時に最新フォーマットで保存し直す（マイグレーション）
            if version != SESSION_FORMAT_VERSION:
                self.save_session(session)
            return session
        # 旧フォーマット（バージョンフィールドなし）
        session = Session.from_dict(raw)
        self.save_session(session)  # マイグレーション
        return session

    def save_session(self, session: Session) -> None:
        data = session.to_dict()
        data["version"] = SESSION_FORMAT_VERSION
        path = self._session_path(session.id)
        self._write_json_atomic(path, data)

    def delete_session(self, session_id: str) -> None:
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()

    def _session_path(self, session_id: str) -> Path:
        safe_id = session_id.replace("/", "_")
        return self._base_dir / f"session_{safe_id}.json"

    def _write_json_atomic(self, path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)



