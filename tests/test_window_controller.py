from __future__ import annotations

from win_llm_chat_pyside.ui.window_controller import WindowController


class DummyWindow:
    def __init__(self, visible: bool = False, active: bool = False, minimized: bool = False) -> None:
        self.visible = visible
        self.active = active
        self.minimized = minimized
        self.raise_calls = 0
        self.activate_calls = 0
        self.show_normal_calls = 0
        self.show_minimized_calls = 0
        self.hide_calls = 0
        self.window_flag_calls: list[tuple[str, bool]] = []

    def isVisible(self) -> bool:  # noqa: N802 - Qt 互換シグネチャ
        return self.visible

    def isActiveWindow(self) -> bool:  # noqa: N802
        return self.active

    def isMinimized(self) -> bool:  # noqa: N802
        return self.minimized

    def showNormal(self) -> None:  # noqa: N802
        self.visible = True
        self.minimized = False
        self.show_normal_calls += 1

    def show(self) -> None:
        self.visible = True

    def showMinimized(self) -> None:  # noqa: N802
        self.visible = True
        self.minimized = True
        self.show_minimized_calls += 1

    def raise_(self) -> None:
        self.raise_calls += 1

    def activateWindow(self) -> None:  # noqa: N802
        self.active = True
        self.activate_calls += 1

    def hide(self) -> None:
        self.visible = False
        self.hide_calls += 1

    def setWindowFlag(self, flag, enabled):  # noqa: N802
        self.window_flag_calls.append((flag, bool(enabled)))


def test_toggle_visibility_shows_window_when_hidden():
    window = DummyWindow()
    controller = WindowController(window)

    controller.toggle_visibility()

    assert window.visible
    assert not window.minimized
    assert window.show_normal_calls >= 1
    assert window.raise_calls == 1
    assert window.activate_calls == 1


def test_toggle_visibility_minimizes_when_active():
    window = DummyWindow(visible=True, active=True, minimized=False)
    controller = WindowController(window)

    controller.toggle_visibility()

    assert window.show_minimized_calls == 1
    assert window.minimized
    assert window.visible


def test_set_always_on_top_updates_window_flag():
    window = DummyWindow()
    controller = WindowController(window)

    controller.set_always_on_top(True)

    assert window.window_flag_calls
    flag, enabled = window.window_flag_calls[-1]
    assert enabled is True

    controller.set_always_on_top(False)
    _, enabled = window.window_flag_calls[-1]
    assert enabled is False


