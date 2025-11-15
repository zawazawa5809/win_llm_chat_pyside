"""添付ファイル要約/Q&A 用のプロンプト生成サービス。"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional

from .models import AttachmentMetadata, Message, Session
from .prompt_template_store import PromptTemplateStore, SYSTEM_TEMPLATE_PREFIX
from .role_profile_store import RoleProfileStore

SUMMARY_TEMPLATE_ID = "file-summary-v1"
QA_TEMPLATE_ID = "file-qa-v1"

SUMMARY_TEMPLATE_TITLE = "[System] File summary"
QA_TEMPLATE_TITLE = "[System] File QA"

SUMMARY_TEMPLATE_BODY = """SYSTEM:
あなたは日本語のビジネスドキュメントを要約するアシスタントです。以下の Markdown 見出しを必ず順序通りに出力してください:
# 概要（3〜5 行）
# 重要なポイント（最大 7 箇条）
# 決定事項・前提
# TODO・アクションアイテム
# リスク・注意点
推測や架空の情報は記載せず、本文に存在しない事実は「不明」と明示してください。

---
USER:
以下はセッション「{session_name}」で添付されたファイルのメタデータと本文です。内容を読み、前述のフォーマットで要約してください。
- ファイル名: {file_name}
- 種別: {mime_type}
- サイズ: {size_kb} KB
- ページ数: {page_count_text}
{warning_text}

本文:
{extracted_text}
"""

QA_TEMPLATE_BODY = """SYSTEM:
あなたは添付ファイルを参照して質問に回答するアシスタントです。回答は日本語で簡潔にまとめ、本文にない情報は推測せず「不明」と明示してください。

---
USER:
以下のファイル内容を読み、質問に回答してください。
- ファイル名: {file_name}
- 種別: {mime_type}
- サイズ: {size_kb} KB
- ページ数: {page_count_text}
{warning_text}

質問:
{question}

本文:
{extracted_text}
"""


@dataclass
class PromptRequest:
    messages: list[Message]
    temperature: float
    top_p: float


class AttachmentPromptService:
    """ファイル要約/Q&A 用のプロンプトを生成する。"""

    def __init__(
        self,
        *,
        template_store: PromptTemplateStore,
        role_profile_store: Optional[RoleProfileStore] = None,
        temperature: float = 0.2,
        top_p: float = 0.9,
        warning_threshold: int = 20_000,
    ) -> None:
        self._template_store = template_store
        self._role_profile_store = role_profile_store
        self._temperature = temperature
        self._top_p = top_p
        self._warning_threshold = warning_threshold
        self._summary_template_id = self._ensure_default_template(
            SUMMARY_TEMPLATE_ID,
            SUMMARY_TEMPLATE_TITLE,
            SUMMARY_TEMPLATE_BODY,
        )
        self._qa_template_id = self._ensure_default_template(
            QA_TEMPLATE_ID,
            QA_TEMPLATE_TITLE,
            QA_TEMPLATE_BODY,
        )

    def build_summary_request(
        self,
        session: Session,
        attachment: AttachmentMetadata,
        extracted_text: str,
    ) -> PromptRequest:
        return self._build_request(
            template_id=self._summary_template_id,
            session=session,
            attachment=attachment,
            extracted_text=extracted_text,
            question=None,
        )

    def build_qa_request(
        self,
        session: Session,
        attachment: AttachmentMetadata,
        extracted_text: str,
        question: str,
    ) -> PromptRequest:
        return self._build_request(
            template_id=self._qa_template_id,
            session=session,
            attachment=attachment,
            extracted_text=extracted_text,
            question=question,
        )

    # ---- internals ----
    def _build_request(
        self,
        *,
        template_id: str,
        session: Session,
        attachment: AttachmentMetadata,
        extracted_text: str,
        question: Optional[str],
    ) -> PromptRequest:
        template_body = self._get_template_body(template_id)
        system_section, user_section = self._split_sections(template_body)
        context = self._build_context(session, attachment, extracted_text, question)
        messages: list[Message] = []

        role_prompt = self._resolve_role_prompt(session.role_profile_id)
        if role_prompt:
            messages.append(Message(role="system", content=role_prompt))
        if system_section:
            messages.append(
                Message(
                    role="system",
                    content=self._render_template(system_section, context),
                )
            )
        messages.append(
            Message(
                role="user",
                content=self._render_template(user_section, context),
            )
        )
        return PromptRequest(messages=messages, temperature=self._temperature, top_p=self._top_p)

    def _build_context(
        self,
        session: Session,
        attachment: AttachmentMetadata,
        extracted_text: str,
        question: Optional[str],
    ) -> Dict[str, str]:
        size_kb = 0
        if attachment.size_bytes:
            size_kb = max(1, math.ceil(max(0, attachment.size_bytes) / 1024))
        page_count_text = str(attachment.page_count) if attachment.page_count else "不明"
        warning_text = self._build_warning_text(attachment)
        return {
            "session_name": session.name,
            "file_name": attachment.filename,
            "mime_type": attachment.mime_type or "不明",
            "size_kb": str(size_kb),
            "page_count_text": page_count_text,
            "warning_text": warning_text,
            "extracted_text": extracted_text.strip(),
            "question": (question or "").strip(),
        }

    def _build_warning_text(self, attachment: AttachmentMetadata) -> str:
        if not attachment.length_warning:
            return ""
        return f"- 注意: 抽出テキストが {self._warning_threshold:,} 文字を超えています。ポイントを絞って要約してください。"

    def _render_template(self, template: str, context: Dict[str, str]) -> str:
        safe_context = defaultdict(str, context)
        return template.format_map(safe_context).strip()

    def _get_template_body(self, template_id: str) -> str:
        for tpl in self._template_store.list_templates(include_system=True):
            if tpl.id == template_id:
                return tpl.body
        raise ValueError(f"テンプレートが見つかりません: {template_id}")

    def _ensure_default_template(self, template_id: str, title: str, body: str) -> str:
        stored = self._template_store.upsert_system_template(template_id, title, body, overwrite=False)
        return stored.id if stored else f"{SYSTEM_TEMPLATE_PREFIX}{template_id}"

    def _split_sections(self, body: str) -> tuple[Optional[str], str]:
        if "\n---\n" not in body:
            return None, body
        system_part, user_part = body.split("\n---\n", 1)
        system_part = system_part.strip()
        user_part = user_part.strip()
        if system_part.upper().startswith("SYSTEM:"):
            system_part = system_part.split(":", 1)[1].strip()
        if user_part.upper().startswith("USER:"):
            user_part = user_part.split(":", 1)[1].strip()
        return (system_part or None, user_part)

    def _resolve_role_prompt(self, profile_id: Optional[str]) -> Optional[str]:
        if not profile_id or not self._role_profile_store:
            return None
        profile = self._role_profile_store.get_profile(profile_id)
        if profile and profile.system_prompt:
            return profile.system_prompt
        return None

