from win_llm_chat_pyside.chat_rich_text_view import ChatRichTextView
from win_llm_chat_pyside.models import Message


def test_set_messages_renders_plain_text(qt_app):
    view = ChatRichTextView()

    view.set_messages(
        [
            Message(role="user", content="hello **world**"),
            Message(role="assistant", content="reply"),
        ]
    )

    assert "hello" in view.toPlainText()
    assert "reply" in view.toPlainText()
    assert view.message_count == 2


def test_append_and_clear_messages(qt_app):
    view = ChatRichTextView()

    view.append_message(Message(role="user", content="first"))
    view.append_message(Message(role="assistant", content="second"))

    assert view.message_count == 2
    assert view.toPlainText().strip().startswith("User")

    view.clear_messages()

    assert view.message_count == 0
    assert view.toPlainText() == ""


def test_replace_message_content_updates_document(qt_app):
    view = ChatRichTextView()
    view.set_messages([Message(role="assistant", content="pending")])

    view.replace_message_content(0, "final answer")

    assert "final answer" in view.toPlainText()


def test_select_all_captures_multiple_messages(qt_app):
    view = ChatRichTextView()
    view.set_messages(
        [
            Message(role="user", content="first line"),
            Message(role="assistant", content="second line"),
        ]
    )

    view.selectAll()
    selected = view.textCursor().selectedText()

    assert "first line" in selected
    assert "second line" in selected

