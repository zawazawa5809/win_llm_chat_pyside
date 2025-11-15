from __future__ import annotations

from typing import Protocol

from PySide6.QtCore import Qt


class _QtWindowLike(Protocol):
    """PySide6.QtWidgets.QMainWindow 互換の最小インターフェース。"""

    def isVisible(self) -> bool:  # noqa: N802 - Qt シグネチャ
        ...

    def isActiveWindow(self) -> bool:  # noqa: N802
        ...

    def isMinimized(self) -> bool:  # noqa: N802
        ...

    def showNormal(self) -> None:  # noqa: N802
        ...

    def show(self) -> None:
        ...

    def showMinimized(self) -> None:  # noqa: N802
        ...

    def raise_(self) -> None:
        ...

    def activateWindow(self) -> None:  # noqa: N802
        ...

    def hide(self) -> None:
        ...


class WindowController:
    """
    メインウィンドウの表示/最小化トグルを集約するユーティリティ。

    Qt 以外のテストダブルでも利用できるよう、duck typing で最小限の API を要求する。
    """

    def __init__(self, window: _QtWindowLike):
        self._window = window
        self._always_on_top = False

    def toggle_visibility(self) -> None:
        """アクティブなら最小化、非表示なら前面化する。"""
        if self._is_visible_and_active():
            self.minimize_or_hide()
        else:
            self.show_and_focus()

    def show_and_focus(self) -> None:
        """ウィンドウを表示し、フォーカスを与える。"""
        if hasattr(self._window, "showNormal"):
            self._window.showNormal()
        else:
            self._window.show()
        if hasattr(self._window, "raise_"):
            self._window.raise_()
        if hasattr(self._window, "activateWindow"):
            self._window.activateWindow()

    def minimize_or_hide(self) -> None:
        """最小化できるなら最小化、出来なければ隠す。"""
        if hasattr(self._window, "showMinimized"):
            self._window.showMinimized()
        elif hasattr(self._window, "hide"):
            self._window.hide()

    def _is_visible_and_active(self) -> bool:
        try:
            return bool(self._window.isVisible() and self._window.isActiveWindow())
        except Exception:  # 念のため安全側
            return False

    def set_always_on_top(self, enabled: bool) -> None:
        """常時最前面フラグを更新する。"""
        self._always_on_top = bool(enabled)
        if hasattr(self._window, "setWindowFlag"):
            try:
                self._window.setWindowFlag(Qt.WindowStaysOnTopHint, self._always_on_top)
            except Exception:
                return
        # Qt はフラグ変更後に再表示すると反映が確実になるため、明示的に前面化する
        try:
            if hasattr(self._window, "showNormal"):
                self._window.showNormal()
            elif hasattr(self._window, "show"):
                self._window.show()
            if hasattr(self._window, "raise_"):
                self._window.raise_()
            if hasattr(self._window, "activateWindow"):
                self._window.activateWindow()
        except Exception:
            # 最前面フラグが適用できなくてもアプリ自体は落とさない
            pass


