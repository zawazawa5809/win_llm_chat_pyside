from win_llm_chat_pyside.features.attachments.attachment_context import AttachmentContextBuilder
from win_llm_chat_pyside.models import AttachmentMetadata, Session


def _session() -> Session:
    attachments = [
        AttachmentMetadata(
            id="a1",
            session_id="s1",
            filename="a.txt",
            size_bytes=1024,
            mime_type="text/plain",
            status="ready",
        ),
        AttachmentMetadata(
            id="a2",
            session_id="s1",
            filename="b.pdf",
            size_bytes=2048,
            mime_type="application/pdf",
            page_count=3,
            status="ready",
        ),
    ]
    attachment_texts = {
        "a1": "本文1\n追加情報",
        "a2": "本文2",
    }
    return Session(
        id="s1",
        name="session",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
        attachments=attachments,
        attachment_texts=attachment_texts,
        messages=[],
    )


def test_build_includes_metadata_and_text():
    builder = AttachmentContextBuilder(default_max_chars=1000)
    session = _session()

    result = builder.build(session, ["a1", "a2"])

    assert "### 添付: a.txt" in result.text
    assert "本文1" in result.text
    assert "### 添付: b.pdf" in result.text
    assert len(result.included_ids) == 2
    assert result.skipped_ids == []
    assert result.truncated is False


def test_build_truncates_when_limit_exceeded():
    builder = AttachmentContextBuilder(default_max_chars=10)
    session = _session()

    result = builder.build(session, ["a1"], max_chars=20)

    assert result.truncated is True
    assert len(result.text) <= 20
    assert len(result.included_ids) == 1


def test_build_skips_missing_text():
    builder = AttachmentContextBuilder()
    session = _session()
    session.attachment_texts.pop("a2")

    result = builder.build(session, ["a1", "a2"])

    assert result.included_ids == ["a1"]
    assert result.skipped_ids == ["a2"]

