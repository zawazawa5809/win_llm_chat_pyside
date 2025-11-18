from win_llm_chat_pyside.chat_document_builder import (
    ChatDocumentBuilder,
    MessageDocumentRegion,
)
from win_llm_chat_pyside.models import Message
from PySide6.QtGui import QTextFrameFormat


def _build_sample_messages() -> list[Message]:
    return [
        Message(role="user", content="**bold** hello"),
        Message(role="assistant", content="plain reply"),
    ]


def test_build_document_returns_regions_with_plain_text(qt_app):
    builder = ChatDocumentBuilder()

    result = builder.build(_build_sample_messages())

    assert len(result.message_regions) == 2
    doc_text = result.document.toPlainText()
    assert "bold" in doc_text
    # Markdown markers should not leak into rendered plain text
    assert "**" not in doc_text
    first_region: MessageDocumentRegion = result.message_regions[0]
    assert first_region.role == "user"
    assert first_region.plain_text.strip().startswith("bold")
    assert first_region.start_position < first_region.end_position
    assert first_region.content_start_position > first_region.start_position


def test_user_and_assistant_regions_use_expected_alignment(qt_app):
    builder = ChatDocumentBuilder()

    result = builder.build(_build_sample_messages())

    user_region = result.message_regions[0]
    assistant_region = result.message_regions[1]
    assert user_region.frame is not None
    assert assistant_region.frame is not None
    assert (
        user_region.frame.frameFormat().position()
        == QTextFrameFormat.Position.FloatRight
    )
    assert (
        assistant_region.frame.frameFormat().position()
        == QTextFrameFormat.Position.FloatLeft
    )

