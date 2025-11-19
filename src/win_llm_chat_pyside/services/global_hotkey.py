from __future__ import annotations

import sys
import threading
from typing import Callable, Optional, Protocol, Tuple

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication

from win_llm_chat_pyside.core.app_logger import app_logger

try:
    import ctypes
    from ctypes import wintypes
except Exception:  # pragma: no cover - non-Windows 環境向けフォールバック
    ctypes = None  # type: ignore[assignment]
    wintypes = None  # type: ignore[assignment]

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

_MODIFIER_MAP = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "meta": MOD_WIN,
    "command": MOD_WIN,
}

_SPECIAL_KEYS = {
    "space": 0x20,
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "esc": 0x1B,
    "escape": 0x1B,
    "backspace": 0x08,
    "delete": 0x2E,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "left": 0x25,
    "right": 0x27,
    "up": 0x26,
    "down": 0x28,
}


class HotkeyBackend(Protocol):
    """OS ごとの RegisterHotKey API をラップするためのプロトコル。"""

    def register_hotkey(self, identifier: int, modifiers: int, virtual_key: int) -> bool:
        ...

    def unregister_hotkey(self, identifier: int) -> bool:
        ...


class Win32HotkeyBackend:
    """ctypes で user32.dll を直接叩くシンプルなバックエンド。"""

    def __init__(self) -> None:
        if ctypes is None:  # pragma: no cover - Windows 以外では None
            raise RuntimeError("ctypes が利用できません")
        self._user32 = ctypes.windll.user32  # type: ignore[attr-defined]

    def register_hotkey(self, identifier: int, modifiers: int, virtual_key: int) -> bool:
        return bool(self._user32.RegisterHotKey(None, identifier, modifiers, virtual_key))

    def unregister_hotkey(self, identifier: int) -> bool:
        return bool(self._user32.UnregisterHotKey(None, identifier))


class _QtHotkeyEventFilter(QAbstractNativeEventFilter):
    """WM_HOTKEY を拾って GlobalHotkeyManager へ通知するイベントフィルタ。"""

    def __init__(self, handler: Callable[[int], None]):
        super().__init__()
        self._handler = handler

    def nativeEventFilter(self, eventType, message):  # noqa: N802 - Qt シグネチャ
        if eventType not in ("windows_generic_MSG", "windows_dispatcher_MSG"):
            return False, 0
        if ctypes is None or wintypes is None:
            return False, 0
        # PySide6 から渡される message は sip.voidptr なので、明示的に int に変換してからキャストする
        try:
            msg_ptr = int(message)
        except TypeError:
            return False, 0
        try:
            msg = ctypes.cast(msg_ptr, ctypes.POINTER(wintypes.MSG)).contents
        except (TypeError, ValueError):
            # 予期しないポインタ形式の場合は安全側で無視する
            return False, 0
        if msg.message == WM_HOTKEY:
            self._handler(msg.wParam)
            return True, 0
        return False, 0


def parse_hotkey(expression: str) -> Tuple[int, int]:
    """'Ctrl+Alt+Space' のような文字列を (modifiers, virtual_key) に変換する。"""
    if not expression or not expression.strip():
        raise ValueError("ホットキーの組み合わせが空です。")
    tokens = [token.strip() for token in expression.split("+") if token.strip()]
    if not tokens:
        raise ValueError("ホットキーの組み合わせが空です。")
    key_token = tokens[-1].lower()
    modifier_tokens = tokens[:-1]
    modifiers = 0
    for token in modifier_tokens:
        value = _MODIFIER_MAP.get(token.lower())
        if value is None:
            raise ValueError(f"サポートされていない修飾キーです: {token}")
        modifiers |= value
    virtual_key = _resolve_virtual_key(key_token)
    return modifiers, virtual_key


def _resolve_virtual_key(token: str) -> int:
    if token in _SPECIAL_KEYS:
        return _SPECIAL_KEYS[token]
    if token.startswith("f") and token[1:].isdigit():
        index = int(token[1:])
        if 1 <= index <= 24:
            return 0x70 + (index - 1)
    if len(token) == 1:
        return ord(token.upper())
    raise ValueError(f"サポートされていないキーです: {token}")


class GlobalHotkeyManager:
    """グローバルホットキーの登録/解除を担うファサード。"""

    def __init__(
        self,
        backend: Optional[HotkeyBackend] = None,
        event_source: Optional[QCoreApplication] = None,
        logger=app_logger,
    ):
        self._backend = backend or self._create_backend()
        self._event_source = event_source or QCoreApplication.instance()
        self._logger = logger
        self._event_filter: Optional[_QtHotkeyEventFilter] = None
        self._callback: Optional[Callable[[], None]] = None
        self._hotkey_id = 1
        self._registered = False
        self._lock = threading.RLock()
        self._install_event_filter_if_needed()

    def apply_settings(
        self,
        enabled: bool,
        combination: Optional[str],
        callback: Optional[Callable[[], None]],
    ) -> Tuple[bool, Optional[str]]:
        """設定に基づいてホットキー登録/解除を行う。"""
        with self._lock:
            if not enabled:
                self._callback = None
                self._unregister_if_needed()
                self._log_info("hotkey.disabled", {})
                return True, None
            if not combination or not combination.strip():
                return False, "ホットキーの入力が空です。"
            if callback is None:
                return False, "ホットキーのコールバックが設定されていません。"
            try:
                modifiers, vk = parse_hotkey(combination)
            except ValueError as exc:
                return False, str(exc)
            self._unregister_if_needed()
            if self._backend is None:
                return False, "この OS ではグローバルホットキーを利用できません。"
            if not self._backend.register_hotkey(self._hotkey_id, modifiers, vk):
                self._log_error(
                    "hotkey.register_failed",
                    {"combination": combination},
                )
                return False, "ホットキーの登録に失敗しました。別のキーに変更してください。"
            self._callback = callback
            self._registered = True
            self._log_info(
                "hotkey.registered",
                {
                    "combination": combination,
                    "modifiers": modifiers,
                    "virtual_key": vk,
                },
            )
            return True, None

    def shutdown(self) -> None:
        """アプリ終了時のクリーンアップ。"""
        with self._lock:
            self._unregister_if_needed()
            if self._event_source and self._event_filter:
                try:
                    self._event_source.removeNativeEventFilter(self._event_filter)
                except Exception:
                    pass
                self._event_filter = None

    def simulate_hotkey(self) -> None:
        """テスト用: ホットキー押下をシミュレートする。"""
        self._handle_hotkey(self._hotkey_id)

    # ---- internal helpers ----
    def _handle_hotkey(self, identifier: int) -> None:
        if identifier != self._hotkey_id:
            return
        callback = self._callback
        if callback is None:
            return
        try:
            callback()
        except Exception:
            self._log_error("hotkey.callback_failed", {})

    def _install_event_filter_if_needed(self) -> None:
        if self._event_filter or self._event_source is None:
            return
        if not sys.platform.startswith("win"):
            return  # Windows 以外は WM_HOTKEY が発火しないのでフィルタ不要
        self._event_filter = _QtHotkeyEventFilter(self._handle_hotkey)
        self._event_source.installNativeEventFilter(self._event_filter)

    def _create_backend(self) -> Optional[HotkeyBackend]:
        if not sys.platform.startswith("win"):
            return None
        try:
            return Win32HotkeyBackend()
        except Exception:
            return None

    def _unregister_if_needed(self) -> None:
        if self._backend and self._registered:
            try:
                self._backend.unregister_hotkey(self._hotkey_id)
            except Exception:
                pass
        self._registered = False

    def _log_info(self, event: str, meta: dict) -> None:
        if self._logger:
            try:
                self._logger.info(event, meta)
            except Exception:
                pass

    def _log_error(self, event: str, meta: dict) -> None:
        if self._logger:
            try:
                self._logger.error(event, meta)
            except Exception:
                pass


__all__ = [
    "GlobalHotkeyManager",
    "HotkeyBackend",
    "MOD_ALT",
    "MOD_CONTROL",
    "MOD_SHIFT",
    "MOD_WIN",
    "parse_hotkey",
]


