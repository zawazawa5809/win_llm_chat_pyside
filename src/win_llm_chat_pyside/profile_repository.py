"""
ProfileRepository: 設定（profiles/current）読み書きと移行の責務を担う薄い層。
"""
from __future__ import annotations

import json
import os
from typing import Tuple, List

from . import config as cfg_mod


def load() -> Tuple[List[cfg_mod.Profile], str]:
    """
    設定ファイルから profiles と current_profile_name を読み込む。
    旧スキーマの場合は冪等移行してから返す。
    """
    p = cfg_mod.get_config_path()
    if not p.exists():
        # デフォルトの単一設定を profiles[0] に見立てる
        cfg = cfg_mod.Config()
        cfg_mod._migrate_single_to_profiles_if_needed(cfg)  # type: ignore[attr-defined]  # profiles[0]=default を設定
        return cfg.profiles, cfg.current_profile_name or "default"

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    cfg = cfg_mod._config_from_dict(data)  # type: ignore[attr-defined,assignment]
    cfg_mod._migrate_single_to_profiles_if_needed(cfg)  # type: ignore[attr-defined]
    return cfg.profiles, cfg.current_profile_name or (cfg.profiles[0].name if cfg.profiles else "default")


def save(profiles: List[cfg_mod.Profile], current: str) -> None:
    """
    profiles と current_profile_name を原子的に保存する。
    他の設定値は欠けていても既定で補完される前提で最小限を書き出す。
    """
    # Config を組み立てて既存の save_config を使用（原子的保存）
    base_url = profiles[0].base_url if profiles else "http://localhost:11434"
    model = profiles[0].model if profiles else "gemma3:4b"
    api_key = profiles[0].api_key if profiles else None
    cfg = cfg_mod.Config(
        base_url=base_url,
        model=model,
        api_key=api_key,
        profiles=profiles,
        current_profile_name=current,
    )
    cfg_mod.save_config(cfg)


def migrate_if_needed(data: dict) -> cfg_mod.Config:
    """
    任意の dict を Config に読み込み、旧スキーマなら profiles へ移行する。
    """
    cfg = cfg_mod._config_from_dict(data)  # type: ignore[attr-defined,assignment]
    cfg_mod._migrate_single_to_profiles_if_needed(cfg)  # type: ignore[attr-defined]
    return cfg


def save_full_config(cfg: cfg_mod.Config) -> None:
    """
    Config 全体を原子的に保存する（冪等）。
    """
    path = cfg_mod.get_config_path()
    tmp = path.with_suffix(".json.tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        # save_config でも原子的保存だが、Repository 内完結のAPIも提供
        import dataclasses
        data = dataclasses.asdict(cfg)
        data["version"] = cfg_mod.CONFIG_FORMAT_VERSION
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

