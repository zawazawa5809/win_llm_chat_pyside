"""
診断情報を収集し、サポート向けに共有しやすい形式へ整形するヘルパ。

Requirements:
- アプリバージョン / Python / OS / 現在プロファイルなどを一括取得
- PII や不要な詳細パスは含めない（必要に応じて diagnostics_show_env_details で詳細を切り替え）
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from typing import Dict

from .config import Config, get_default_logs_dir, get_data_dir, get_current_profile
from . import __version__ as APP_VERSION


@dataclass
class DiagnosticsInfo:
    values: Dict[str, str]


class DiagnosticsInfoProvider:
    """診断情報の収集とテキスト整形を行う。"""

    def __init__(self, config: Config) -> None:
        self._config = config

    def collect(self) -> DiagnosticsInfo:
        cfg = self._config
        profile = get_current_profile(cfg)
        vals: Dict[str, str] = {
            "app_version": APP_VERSION,
            "python_version": sys.version.split()[0],
            "os": platform.platform(terse=True),
            "profile_name": profile.name if profile else (cfg.current_profile_name or "n/a"),
            "profile_type": profile.type if profile else "n/a",
            "logging_enabled": str(getattr(cfg, "logging_enabled", True)),
            "logging_level": str(getattr(cfg, "logging_level", "info")),
        }
        # 必要に応じて少しだけ詳細情報を足す（パスは diagnostics_show_env_details が True の場合のみ）
        if getattr(cfg, "diagnostics_show_env_details", False):
            try:
                vals["data_dir"] = str(get_data_dir())
                vals["logs_dir"] = str(get_default_logs_dir())
            except Exception:
                # 診断情報に失敗してもアプリは継続させる
                pass
        return DiagnosticsInfo(values=vals)

    @staticmethod
    def format_text(info: DiagnosticsInfo) -> str:
        """キー=値 形式のテキストに整形する。"""
        lines = [f"{key}: {value}" for key, value in info.values.items()]
        return "\n".join(lines)



