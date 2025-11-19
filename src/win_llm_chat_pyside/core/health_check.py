"""
簡易ヘルスチェックと自己診断機能。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from win_llm_chat_pyside.core.config import Config, get_data_dir, get_sessions_dir, get_prompt_assets_dir, get_default_logs_dir, get_current_profile, validate_profile
from win_llm_chat_pyside.core.app_logger import app_logger


@dataclass
class HealthCheckResult:
    """ヘルスチェック結果。"""
    is_healthy: bool
    issues: List[str]
    warnings: List[str]


class HealthChecker:
    """アプリケーションの簡易ヘルスチェックを実行する。"""

    def __init__(self, config: Config) -> None:
        self._config = config

    def check(self) -> HealthCheckResult:
        """ヘルスチェックを実行する。"""
        issues: List[str] = []
        warnings: List[str] = []

        # 1. 設定値の妥当性チェック
        is_valid, error_msg = self._config.validate()
        if not is_valid:
            issues.append(f"設定が無効です: {error_msg}")

        # 2. プロファイルの検証
        profile = get_current_profile(self._config)
        if profile:
            is_valid, error_msg = validate_profile(profile)
            if not is_valid:
                issues.append(f"現在のプロファイルが無効です: {error_msg}")
        else:
            warnings.append("現在のプロファイルが設定されていません")

        # 3. 必要ディレクトリの存在確認
        try:
            data_dir = get_data_dir()
            if not data_dir.exists():
                issues.append(f"データディレクトリが存在しません: {data_dir}")
            elif not data_dir.is_dir():
                issues.append(f"データディレクトリがディレクトリではありません: {data_dir}")
            elif not self._is_writable(data_dir):
                issues.append(f"データディレクトリに書き込み権限がありません: {data_dir}")
        except Exception as e:
            issues.append(f"データディレクトリの確認に失敗しました: {e}")

        try:
            sessions_dir = get_sessions_dir(self._config)
            if not sessions_dir.exists():
                warnings.append(f"セッションディレクトリが存在しません（初回起動時は正常）: {sessions_dir}")
            elif not self._is_writable(sessions_dir):
                issues.append(f"セッションディレクトリに書き込み権限がありません: {sessions_dir}")
        except Exception as e:
            warnings.append(f"セッションディレクトリの確認に失敗しました: {e}")

        try:
            assets_dir = get_prompt_assets_dir(self._config)
            if not assets_dir.exists():
                warnings.append(f"プロンプトアセットディレクトリが存在しません（初回起動時は正常）: {assets_dir}")
            elif not self._is_writable(assets_dir):
                issues.append(f"プロンプトアセットディレクトリに書き込み権限がありません: {assets_dir}")
        except Exception as e:
            warnings.append(f"プロンプトアセットディレクトリの確認に失敗しました: {e}")

        try:
            logs_dir = get_default_logs_dir()
            if not logs_dir.exists():
                warnings.append(f"ログディレクトリが存在しません（初回起動時は正常）: {logs_dir}")
            elif not self._is_writable(logs_dir):
                warnings.append(f"ログディレクトリに書き込み権限がありません: {logs_dir}")
        except Exception as e:
            warnings.append(f"ログディレクトリの確認に失敗しました: {e}")

        # 4. ログ設定の確認
        if not getattr(self._config, "logging_enabled", True):
            warnings.append("ログが無効になっています。トラブルシューティングが困難になる可能性があります。")

        is_healthy = len(issues) == 0

        return HealthCheckResult(
            is_healthy=is_healthy,
            issues=issues,
            warnings=warnings,
        )

    @staticmethod
    def _is_writable(path: Path) -> bool:
        """パスが書き込み可能かどうかを確認する。"""
        try:
            if not path.exists():
                # 親ディレクトリが書き込み可能か確認
                parent = path.parent
                if not parent.exists():
                    return False
                return parent.is_dir() and (parent.stat().st_mode & 0o200) != 0
            if not path.is_dir():
                return False
            # ディレクトリに書き込み権限があるか確認
            return (path.stat().st_mode & 0o200) != 0
        except Exception:
            return False

    def check_and_log(self) -> HealthCheckResult:
        """ヘルスチェックを実行し、結果をログに記録する。"""
        result = self.check()
        if result.is_healthy:
            if result.warnings:
                app_logger.info("health_check.passed_with_warnings", {
                    "warning_count": len(result.warnings),
                })
            else:
                app_logger.info("health_check.passed", {})
        else:
            app_logger.error("health_check.failed", {
                "issue_count": len(result.issues),
                "warning_count": len(result.warnings),
            })
        return result

