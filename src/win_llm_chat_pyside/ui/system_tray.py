from __future__ import annotations

from typing import Callable

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from win_llm_chat_pyside.ui.window_controller import WindowController


class SystemTrayManager:
    """QSystemTrayIcon を管理し、ウィンドウ操作を提供するコンポーネント。"""

    def __init__(
        self,
        parent: QWidget,
        window: QWidget,
        window_controller: WindowController,
        on_exit_requested: Callable[[], None],
    ) -> None:
        self._window = window
        self._window_controller = window_controller
        self._tray_icon = QSystemTrayIcon(self._resolve_icon(window), parent)
        self._menu = QMenu(parent)
        self._toggle_action = self._menu.addAction("開く/隠す")
        self._toggle_action.triggered.connect(self._toggle_window)  # type: ignore[attr-defined]

        exit_action = self._menu.addAction("終了")
        exit_action.triggered.connect(on_exit_requested)  # type: ignore[attr-defined]

        self._tray_icon.setContextMenu(self._menu)
        self._tray_icon.setToolTip(window.windowTitle())
        self._tray_icon.activated.connect(self._on_activated)  # type: ignore[attr-defined]
        self._tray_icon.show()
        self._sync_toggle_label()

    @property
    def is_available(self) -> bool:
        """システムトレイが利用可能かどうか。"""

        return QSystemTrayIcon.isSystemTrayAvailable()

    def hide(self) -> None:
        """トレイアイコンを非表示にする。"""

        self._tray_icon.hide()

    def _toggle_window(self) -> None:
        if self._window.isVisible() and not self._window.isMinimized():
            self._window_controller.minimize_or_hide()
        else:
            self._window_controller.show_and_focus()
        self._sync_toggle_label()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._window_controller.show_and_focus()
            self._sync_toggle_label()

    def _sync_toggle_label(self) -> None:
        label = "隠す" if self._window.isVisible() and not self._window.isMinimized() else "開く"
        self._toggle_action.setText(f"{label}")

    def _resolve_icon(self, window: QWidget) -> QIcon:
        icon = window.windowIcon()
        if not icon or icon.isNull():
            icon = QApplication.windowIcon()
        return icon
