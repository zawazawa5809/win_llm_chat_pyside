from PySide6.QtTest import QTest

from win_llm_chat_pyside.ui.main_window import MainWindow


def _show_window(window: MainWindow) -> None:
    window.show()
    window.raise_()
    window.activateWindow()
    QTest.qWait(30)


def test_main_tabs_exist_and_labels(qt_app):  # noqa: ARG001
    window = MainWindow()
    assert window.main_tabs is not None
    assert window.main_tabs.count() == 2
    assert window.main_tabs.tabText(0) == "チャット"
    assert window.main_tabs.tabText(1) == "添付"
    assert window.main_tabs.tabToolTip(0)
    assert window.main_tabs.tabToolTip(1)


def test_ctrl_1_and_2_shortcuts_registered(qt_app):  # noqa: ARG001
    window = MainWindow()
    keys = {meta.key for meta in window.shortcut_registry.all()}
    assert "Ctrl+1" in keys
    assert "Ctrl+2" in keys


def test_switch_main_tab_helper_changes_index_and_focus_chat(qt_app):  # noqa: ARG001
    window = MainWindow()
    _show_window(window)
    assert window.main_tabs is not None

    window._switch_main_tab("chat")
    assert window.main_tabs.currentIndex() == 0
    assert window.input_field.hasFocus()


def test_switch_main_tab_helper_focuses_search_when_no_attachments(qt_app):  # noqa: ARG001
    window = MainWindow()
    _show_window(window)
    assert window.main_tabs is not None

    # 添付がない状態として振る舞わせる
    window._has_attachments = False  # type: ignore[assignment]
    line_edit = window.attachment_search_panel._search_bar.line_edit()  # type: ignore[assignment]
    line_edit.setText("foo")

    window._switch_main_tab("attachments")
    assert window.main_tabs.currentIndex() == 1
    # フォーカス処理によりテキストが選択されていることを期待
    assert line_edit.selectedText() == "foo"

