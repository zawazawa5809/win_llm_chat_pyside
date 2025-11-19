from __future__ import annotations

from pathlib import Path

import pytest

from win_llm_chat_pyside.features.attachments.attachment_prompts import (
    AttachmentPromptService,
)
from win_llm_chat_pyside.models import AttachmentMetadata, Message, Session
from win_llm_chat_pyside.features.prompts.prompt_repository import TemplateRepository, RoleProfileRepository
from win_llm_chat_pyside.features.prompts.prompt_template_store import PromptTemplateStore
from win_llm_chat_pyside.features.roles.role_profile_store import RoleProfileStore


def _create_services(tmp_path: Path) -> tuple[AttachmentPromptService, Session, AttachmentMetadata]:
    template_repo = TemplateRepository(tmp_path / "prompts")
    role_repo = RoleProfileRepository(tmp_path / "prompts")
    template_store = PromptTemplateStore(template_repo)
    role_store = RoleProfileStore(role_repo)
    service = AttachmentPromptService(
        template_store=template_store,
        role_profile_store=role_store,
        warning_threshold=5,
    )
    session = Session(
        id="sess-1",
        name="案件A",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        messages=[Message(role="system", content="You are helpful.")],
    )
    attachment = AttachmentMetadata(
        id="att-1",
        session_id=session.id,
        filename="doc.pdf",
        size_bytes=2048,
        mime_type="application/pdf",
        page_count=2,
        text_length=10,
        status="ready",
        length_warning=True,
    )
    return service, session, attachment


def test_summary_prompt_includes_metadata_and_warning(tmp_path: Path):
    service, session, attachment = _create_services(tmp_path)
    result = service.build_summary_request(session, attachment, "本文")

    assert result.temperature == pytest.approx(0.2)
    assert len(result.messages) >= 2
    summary_prompt = result.messages[-1].content
    assert "doc.pdf" in summary_prompt
    assert "本文" in summary_prompt
    assert "注意" in summary_prompt


def test_qa_prompt_includes_question(tmp_path: Path):
    service, session, attachment = _create_services(tmp_path)
    result = service.build_qa_request(session, attachment, "抜粋テキスト", question="期限はいつですか？")

    user_message = result.messages[-1].content
    assert "期限はいつですか？" in user_message
    assert "抜粋テキスト" in user_message


