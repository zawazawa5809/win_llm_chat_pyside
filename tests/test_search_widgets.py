
from win_llm_chat_pyside.features.search.search_widgets import AttachmentSearchPanel, SearchBarBase


def test_search_bar_base_emits_search_signal(qt_app):  # noqa: ARG001
    bar = SearchBarBase(
        label_text="検索",
        placeholder_text="キーワード",
        auto_search=True,
        show_navigation=True,
        show_close_button=True,
    )
    captured: list[str] = []
    bar.search_requested.connect(captured.append)

    bar.show_bar()
    bar.line_edit().setText("hello")

    assert captured[-1] == "hello"


def test_search_bar_navigation_buttons_emit_signals(qt_app):  # noqa: ARG001
    bar = SearchBarBase(label_text="検索", placeholder_text="kw")
    next_calls: list[bool] = []
    prev_calls: list[bool] = []
    bar.next_requested.connect(lambda: next_calls.append(True))
    bar.previous_requested.connect(lambda: prev_calls.append(True))

    bar.next_button().click()
    bar.previous_button().click()

    assert next_calls
    assert prev_calls


def test_search_bar_update_status_formats_counts(qt_app):  # noqa: ARG001
    bar = SearchBarBase(label_text="検索", placeholder_text="kw")
    bar.update_status(current=0, total=0)
    assert bar.status_label().text() == "0 / 0"

    bar.update_status(current=2, total=5)
    assert bar.status_label().text() == "2 / 5"


def test_search_bar_close_hides_and_emits_signal(qt_app):  # noqa: ARG001
    bar = SearchBarBase(label_text="検索", placeholder_text="kw")
    closed = []
    bar.closed.connect(lambda: closed.append(True))

    bar.show_bar()
    assert bar.isVisible()

    bar.close_button().click()

    assert not bar.isVisible()
    assert closed


def test_attachment_search_panel_focuses_input(qt_app):  # noqa: ARG001
    panel = AttachmentSearchPanel()
    panel.show()
    line_edit = panel._search_bar.line_edit()
    line_edit.setText("search text")

    panel.focus_search_input()

    assert line_edit.hasSelectedText()
    assert line_edit.selectedText() == "search text"

