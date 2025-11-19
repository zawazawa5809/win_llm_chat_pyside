from win_llm_chat_pyside.models import Message
from win_llm_chat_pyside.ui.main_window import MainWindow


def test_update_chat_view_populates_rich_text_view(qt_app):
    window = MainWindow()
    try:
        window.messages = [
            Message(role="user", content="hello"),
            Message(role="assistant", content="world"),
        ]
        window._update_chat_view()

        assert "hello" in window.chat_view.toPlainText()
        assert "world" in window.chat_view.toPlainText()
        assert window.chat_view.message_count == 2
    finally:
        window.close()


def test_session_search_highlights_and_scrolls(qt_app):
    window = MainWindow()
    try:
        window.messages = [
            Message(role="user", content="find me"),
            Message(role="assistant", content="no match"),
        ]
        window._update_chat_view()

        window._on_session_search_requested("find")

        selections = window.chat_view.extraSelections()
        assert len(selections) >= 1
    finally:
        window.close()


def test_chat_font_respects_config_settings(qt_app):
    window = MainWindow()
    try:
        window.config.ui_markdown_font_family = "Courier New"
        window.config.ui_markdown_font_size_pt = 13

        window._apply_chat_font_from_config()

        font = window.chat_view.font()
        # family は OS によって解決結果が微妙に違う可能性があるので、サイズを主に確認
        assert font.pointSize() == 13
    finally:
        window.close()

