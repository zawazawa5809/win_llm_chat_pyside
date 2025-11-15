"""
RoleProfileStore: 役割プロファイルを操作するロジック層。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from .models import RoleProfile
from .prompt_repository import RoleProfileRepository


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class RoleProfileStore:
    """RoleProfileRepository を包んで検証・既定制御を担う。"""

    def __init__(self, repository: RoleProfileRepository):
        self._repo = repository
        self._profiles: List[RoleProfile] = self._repo.load_profiles()
        self._normalize_defaults()

    def list_profiles(self) -> List[RoleProfile]:
        return list(self._profiles)

    def get_profile(self, profile_id: str) -> Optional[RoleProfile]:
        for profile in self._profiles:
            if profile.id == profile_id:
                return profile
        return None

    def get_default_profile(self) -> Optional[RoleProfile]:
        for profile in self._profiles:
            if profile.is_default:
                return profile
        return None

    def create_profile(self, name: str, system_prompt: str, make_default: bool = True) -> RoleProfile:
        name = name.strip()
        if not name:
            raise ValueError("役割プロファイル名を入力してください。")
        now = _now()
        profile = RoleProfile(
            id=uuid.uuid4().hex,
            name=name,
            system_prompt=system_prompt.strip(),
            created_at=now,
            updated_at=now,
            is_default=False,
        )
        self._profiles.append(profile)
        if make_default or not any(p.is_default for p in self._profiles):
            self._set_default_internal(profile.id)
        self._persist()
        return profile

    def update_profile(
        self,
        profile_id: str,
        name: str,
        system_prompt: str,
        *,
        make_default: bool | None = None,
    ) -> RoleProfile:
        profile = self._find(profile_id)
        name = name.strip()
        if not name:
            raise ValueError("役割プロファイル名を入力してください。")
        profile.name = name
        profile.system_prompt = system_prompt.strip()
        profile.updated_at = _now()
        if make_default is True:
            self._set_default_internal(profile_id)
        elif make_default is False and profile.is_default:
            profile.is_default = False
            if not any(p.is_default for p in self._profiles):
                self._set_default_internal(profile_id)
        self._persist()
        return profile

    def delete_profile(self, profile_id: str) -> None:
        before = len(self._profiles)
        self._profiles = [p for p in self._profiles if p.id != profile_id]
        if len(self._profiles) == before:
            raise ValueError("役割プロファイルが見つかりません。")
        if not any(p.is_default for p in self._profiles) and self._profiles:
            self._profiles[0].is_default = True
        self._persist()

    def set_default(self, profile_id: str) -> RoleProfile:
        profile = self._set_default_internal(profile_id)
        self._persist()
        return profile

    # ---- internal helpers ----
    def _find(self, profile_id: str) -> RoleProfile:
        for profile in self._profiles:
            if profile.id == profile_id:
                return profile
        raise ValueError("役割プロファイルが見つかりません。")

    def _set_default_internal(self, profile_id: str) -> RoleProfile:
        target = self._find(profile_id)
        for profile in self._profiles:
            profile.is_default = profile.id == profile_id
        return target

    def _normalize_defaults(self) -> None:
        defaults = [p for p in self._profiles if p.is_default]
        if len(defaults) <= 1:
            if not defaults and self._profiles:
                self._profiles[0].is_default = True
            return
        # 先頭以外の default を解除
        keeper = defaults[0].id
        for profile in self._profiles:
            profile.is_default = profile.id == keeper

    def _persist(self) -> None:
        self._repo.save_profiles(self._profiles)


