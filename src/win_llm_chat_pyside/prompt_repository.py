"""
プロンプトテンプレートと役割プロファイルの永続化を扱う Repository。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, List

from .app_logger import app_logger
from .models import PromptTemplate, RoleProfile

# 現在のフォーマットバージョン
TEMPLATE_FORMAT_VERSION = "1.6"
ROLE_PROFILE_FORMAT_VERSION = "1.6"


class TemplateRepository:
    """テンプレート一覧の JSON 永続化。"""

    def __init__(self, base_dir: Path):
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._base_dir / "templates.json"

    def load_templates(self) -> List[PromptTemplate]:
        data = self._read_json(self._path)
        if not data:
            return []
        version = data.get("version", "1.0")
        items = data.get("templates", [])
        if not isinstance(items, list):
            return []
        templates = [PromptTemplate.from_dict(item) for item in items if isinstance(item, dict)]
        # 読み込み時に最新フォーマットで保存し直す（マイグレーション）
        if version != TEMPLATE_FORMAT_VERSION:
            self.save_templates(templates)
        return templates

    def save_templates(self, templates: Iterable[PromptTemplate]) -> None:
        payload = {
            "version": TEMPLATE_FORMAT_VERSION,
            "templates": [tpl.to_dict() for tpl in templates],
        }
        self._write_json_atomic(self._path, payload)

    def _read_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError) as exc:  # noqa: BLE001
            try:
                app_logger.warning("prompt.templates.load_failed", {"error": str(exc)})
            except Exception:
                pass
        return {}

    def _write_json_atomic(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except Exception as exc:  # noqa: BLE001
            try:
                if tmp.exists():
                    tmp.unlink()
                app_logger.error("prompt.templates.save_failed", {"error": str(exc)})
            except Exception:
                pass
            raise


class RoleProfileRepository:
    """役割プロファイルの JSON 永続化。"""

    def __init__(self, base_dir: Path):
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._base_dir / "role_profiles.json"

    def load_profiles(self) -> List[RoleProfile]:
        data = self._read_json(self._path)
        if not data:
            return []
        version = data.get("version", "1.0")
        items = data.get("profiles", [])
        if not isinstance(items, list):
            return []
        profiles = [RoleProfile.from_dict(item) for item in items if isinstance(item, dict)]
        # 読み込み時に最新フォーマットで保存し直す（マイグレーション）
        if version != ROLE_PROFILE_FORMAT_VERSION:
            self.save_profiles(profiles)
        return profiles

    def save_profiles(self, profiles: Iterable[RoleProfile]) -> None:
        payload = {
            "version": ROLE_PROFILE_FORMAT_VERSION,
            "profiles": [profile.to_dict() for profile in profiles],
        }
        self._write_json_atomic(self._path, payload)

    def _read_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError) as exc:  # noqa: BLE001
            try:
                app_logger.warning("prompt.role_profiles.load_failed", {"error": str(exc)})
            except Exception:
                pass
        return {}

    def _write_json_atomic(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except Exception as exc:  # noqa: BLE001
            try:
                if tmp.exists():
                    tmp.unlink()
                app_logger.error("prompt.role_profiles.save_failed", {"error": str(exc)})
            except Exception:
                pass
            raise


