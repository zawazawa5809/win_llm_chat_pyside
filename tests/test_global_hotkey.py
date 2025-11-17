from __future__ import annotations

from win_llm_chat_pyside.global_hotkey import GlobalHotkeyManager, MOD_ALT, MOD_CONTROL


class FakeBackend:
    def __init__(self) -> None:
        self.register_calls: list[tuple[int, int, int]] = []
        self.unregister_calls: int = 0
        self.should_register = True

    def register_hotkey(self, identifier: int, modifiers: int, virtual_key: int) -> bool:
        self.register_calls.append((identifier, modifiers, virtual_key))
        return self.should_register

    def unregister_hotkey(self, identifier: int) -> bool:
        self.unregister_calls += 1
        return True


def _noop_callback() -> None:
    pass


def test_apply_settings_registers_and_triggers_callback():
    backend = FakeBackend()
    called: list[str] = []
    manager = GlobalHotkeyManager(backend=backend, event_source=None, logger=None)

    success, error = manager.apply_settings(True, "Ctrl+Alt+Space", lambda: called.append("hit"))

    assert success
    assert error is None
    assert backend.register_calls, "register_hotkey が呼び出されていません"
    _, modifiers, vk = backend.register_calls[-1]
    assert modifiers == (MOD_CONTROL | MOD_ALT)
    assert vk == 0x20  # Space キー

    manager.simulate_hotkey()
    assert called == ["hit"]


def test_apply_settings_unregisters_when_disabled():
    backend = FakeBackend()
    manager = GlobalHotkeyManager(backend=backend, event_source=None, logger=None)

    manager.apply_settings(True, "Ctrl+Alt+Space", _noop_callback)
    assert backend.register_calls

    success, error = manager.apply_settings(False, "Ctrl+Alt+Space", _noop_callback)

    assert success
    assert error is None
    assert backend.unregister_calls == 1
    # 非アクティブ時にホットキーが発火しても何も起きない
    manager.simulate_hotkey()  # 例外なく無視されることを期待


def test_apply_settings_returns_error_when_registration_fails():
    backend = FakeBackend()
    backend.should_register = False
    manager = GlobalHotkeyManager(backend=backend, event_source=None, logger=None)

    success, error = manager.apply_settings(True, "Ctrl+Alt+Space", _noop_callback)

    assert not success
    assert error is not None
    assert "登録" in error or "hotkey" in error.lower()
    assert not backend.unregister_calls


