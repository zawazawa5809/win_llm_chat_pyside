from win_llm_chat_pyside.features.chat.chat_rich_text_view import ChatRichTextView
from win_llm_chat_pyside.features.chat.chat_search_highlighter import ChatSearchHighlighter
from win_llm_chat_pyside.models import Message
from win_llm_chat_pyside.features.search.search_services import SessionHit


def _prepare_view() -> ChatRichTextView:
    view = ChatRichTextView()
    view.set_messages(
        [
            Message(role="assistant", content="find keyword here"),
            Message(role="user", content="nothing to see"),
        ]
    )
    return view


def test_apply_hits_marks_extra_selections(qt_app):
    view = _prepare_view()
    highlighter = ChatSearchHighlighter(view)
    hit = SessionHit(message_index=0, start=5, length=7)

    highlighter.apply_hits([hit])

    selections = view.extraSelections()
    assert len(selections) == 1


def test_focus_hit_moves_cursor(qt_app):
    view = _prepare_view()
    highlighter = ChatSearchHighlighter(view)
    hit = SessionHit(message_index=0, start=5, length=7)
    highlighter.apply_hits([hit])

    highlighter.focus_hit(0)

    region = view.message_regions[0]
    expected_start = region.content_start_position + hit.start
    selection_start = view.textCursor().selectionStart()
    assert selection_start == expected_start

