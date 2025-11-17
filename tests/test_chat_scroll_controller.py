from PySide6.QtWidgets import QTextBrowser

from win_llm_chat_pyside.chat_scroll_controller import ChatScrollController


def test_scroll_controller_scrolls_to_end_when_allowed(qt_app):  # noqa: ARG001
    view = QTextBrowser()
    view.setPlainText("\n".join(f"line {i}" for i in range(200)))
    controller = ChatScrollController(view)

    controller.scroll_to_end()

    assert view.verticalScrollBar().value() == view.verticalScrollBar().maximum()


def test_scroll_controller_respects_user_override_until_forced(qt_app):  # noqa: ARG001
    view = QTextBrowser()
    view.setPlainText("\n".join(f"line {i}" for i in range(200)))
    controller = ChatScrollController(view)
    controller.scroll_to_end()

    view.verticalScrollBar().setValue(0)
    controller.scroll_to_end()
    assert view.verticalScrollBar().value() == 0

    controller.scroll_to_end(force=True)
    assert view.verticalScrollBar().value() == view.verticalScrollBar().maximum()

