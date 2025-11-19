from win_llm_chat_pyside.features.chat.chat_rich_text_view import ChatRichTextView
from win_llm_chat_pyside.features.chat.chat_streaming_updater import ChatStreamingUpdater
from win_llm_chat_pyside.models import Message


def test_streaming_updates_view_incrementally(qt_app):
    view = ChatRichTextView()
    view.set_messages([Message(role="assistant", content="")])
    updater = ChatStreamingUpdater(view)

    updater.begin(message_index=0)
    updater.update_text("Hello")
    updater.update_text("Hello World")

    assert "Hello World" in view.toPlainText()


def test_streaming_cancel_stops_updates(qt_app):
    view = ChatRichTextView()
    view.set_messages([Message(role="assistant", content="init")])
    updater = ChatStreamingUpdater(view)

    updater.begin(message_index=0)
    updater.cancel()
    updater.update_text("ignored")

    assert "ignored" not in view.toPlainText()

