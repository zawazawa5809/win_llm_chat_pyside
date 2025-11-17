"""
アプリ全体で共有するロギングファサード。

Requirements:
- Config の logging.* 設定を尊重し、RotatingFileHandler でローカルファイルへ出力
- センシティブな情報（prompt/content/api_key 等）はフィルタリング
- UI などからは event 名とメタ情報を渡すだけでよいシンプルな API を提供
"""

from __future__ import annotations

import json
import logging
import threading
from logging import Handler
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from .config import Config, get_default_logs_dir

_SENSITIVE_KEYS = {
    "prompt",
    "prompts",
    "content",
    "contents",
    "body",
    "payload",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "token",
    "messages",
}


class AppLogger:
    """軽量なアプリケーションロガー。"""

    def __init__(self) -> None:
        self._logger = logging.getLogger("win_llm_chat_pyside")
        self._logger.propagate = False
        self._handler: Optional[Handler] = None
        self._enabled: bool = True
        self._log_dir: Optional[Path] = None
        self._configured = False
        # configure() 内から handler 差し替え→get_log_dir() を呼ぶため再入可能なロックが必要
        self._lock = threading.RLock()

    def configure(self, config: Config) -> None:
        """Config の内容からロガーを再初期化する。"""
        with self._lock:
            self._enabled = bool(getattr(config, "logging_enabled", True))
            self._log_dir = self._resolve_log_dir(getattr(config, "logging_dir", None))
            log_level_name = str(getattr(config, "logging_level", "info")).upper()
            level = getattr(logging, log_level_name, logging.INFO)
            self._logger.setLevel(level)
            self._replace_handler(
                max_bytes=max(
                    1024,
                    int(getattr(config, "logging_max_file_size_mb", 5)) * 1024 * 1024,
                ),
                backup_count=max(1, int(getattr(config, "logging_rotation_keep_files", 5))),
            )
            self._configured = True

    def info(self, event: str, meta: Optional[Dict[str, Any]] = None) -> None:
        self._log(logging.INFO, event, meta)

    def error(self, event: str, meta: Optional[Dict[str, Any]] = None) -> None:
        self._log(logging.ERROR, event, meta)

    def warning(self, event: str, meta: Optional[Dict[str, Any]] = None) -> None:
        self._log(logging.WARNING, event, meta)

    def get_log_dir(self) -> Path:
        """現在のログディレクトリ（存在しなければ既定値を作成して返す）。"""
        with self._lock:
            if self._log_dir and self._log_dir.exists():
                return self._log_dir
            self._log_dir = get_default_logs_dir()
            return self._log_dir

    # ---- internal helpers ----
    def _log(self, level: int, event: str, meta: Optional[Dict[str, Any]]) -> None:
        if not self._enabled:
            return
        if not self._configured:
            # Config 未適用でもエラーにはしない（stdout へ出力）
            logging.basicConfig(level=logging.INFO)
            self._configured = True
        sanitized = self._sanitize_meta(meta or {})
        try:
            payload = json.dumps(sanitized, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            payload = repr(sanitized)
        message = f"{event} {payload}"
        self._logger.log(level, message)

    def _replace_handler(self, max_bytes: int, backup_count: int) -> None:
        if self._handler:
            self._logger.removeHandler(self._handler)
            self._handler.close()
            self._handler = None
        if not self._enabled:
            return
        log_dir = self.get_log_dir()
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            handler: Handler = RotatingFileHandler(
                log_dir / "app.log",
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
        except OSError as exc:  # フォルダ作成/ファイル生成に失敗した場合は stdout へフォールバック
            print(f"[app_logger] ファイルロガーを初期化できませんでした: {exc}")
            handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)
        self._handler = handler

    def close(self) -> None:
        """ハンドラを明示的にクローズする（主にテスト用/終了処理用）。"""
        with self._lock:
            if self._handler:
                self._logger.removeHandler(self._handler)
                self._handler.close()
                self._handler = None

    def _sanitize_meta(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        sanitized: Dict[str, Any] = {}
        for key, value in meta.items():
            rendered = self._render_value(key, value)
            sanitized[key] = rendered
        return sanitized

    def _render_value(self, key: str, value: Any) -> Any:
        lowered = key.lower()
        if lowered in _SENSITIVE_KEYS or any(token in lowered for token in ("prompt", "content", "api", "token")):
            return "[filtered]"
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        text = str(value)
        if len(text) > 300:
            text = text[:300] + "…"
        return text

    def _resolve_log_dir(self, configured_path: Optional[str]) -> Path:
        if configured_path:
            try:
                path = Path(configured_path).expanduser()
                path.mkdir(parents=True, exist_ok=True)
                return path
            except OSError:
                pass  # フォールバックして既定の logs ディレクトリを使用
        return get_default_logs_dir()


app_logger = AppLogger()


