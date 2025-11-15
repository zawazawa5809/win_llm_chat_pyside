from win_llm_chat_pyside.models import Message, SessionSummary
from win_llm_chat_pyside.search_services import (
    SessionSearchService,
    AttachmentSearchService,
    AttachmentSearchInput,
)


def test_session_search_service_finds_hits_case_insensitive():
    service = SessionSearchService()
    messages = [
        Message(role="user", content="Hello World"),
        Message(role="assistant", content="worldwide knowledge base"),
        Message(role="assistant", content="nothing here"),
    ]
    hits = service.search_in_session(messages, "world")
    assert len(hits) == 2
    assert hits[0].message_index == 0
    assert hits[1].message_index == 1


def test_session_search_service_searches_summaries():
    service = SessionSearchService()
    summaries = [
        SessionSummary(id="s1", name="Design Notes", updated_at="2025-11-15T00:00:00Z", preview_text="keyword alpha beta"),
        SessionSummary(id="s2", name="Meeting", updated_at="2025-11-15T00:00:00Z", preview_text="random text"),
    ]
    result = service.search_in_summaries(summaries, "alpha")
    assert result == ["s1"]


def test_attachment_search_service_counts_hits_and_snippets():
    service = AttachmentSearchService()
    attachments = [
        AttachmentSearchInput(
            attachment_id="att1",
            filename="report.txt",
            text="Foo bar\nfoo baz\nsomething else",
        ),
        AttachmentSearchInput(
            attachment_id="att2",
            filename="notes.txt",
            text="irrelevant content",
        ),
    ]
    hits = service.search_in_attachments(attachments, "foo")
    assert len(hits) == 1
    hit = hits[0]
    assert hit.attachment_id == "att1"
    assert hit.hit_count == 2
    assert "foo" in hit.snippet.lower()


def test_attachment_search_service_matches_filename_when_text_missing():
    service = AttachmentSearchService()
    attachments = [
        AttachmentSearchInput(
            attachment_id="attX",
            filename="AGENTS.md",
            text="custom files are supported.",
        )
    ]
    hits = service.search_in_attachments(attachments, "agen")
    assert len(hits) == 1
    assert hits[0].attachment_id == "attX"
    assert hits[0].snippet == "[ファイル名に一致]"

