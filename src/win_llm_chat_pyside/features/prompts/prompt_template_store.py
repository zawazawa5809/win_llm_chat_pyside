"""
PromptTemplateStore: テンプレート一覧の CRUD を担う純粋ロジック層。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from win_llm_chat_pyside.models import PromptTemplate
from win_llm_chat_pyside.features.prompts.prompt_repository import TemplateRepository


SYSTEM_TEMPLATE_PREFIX = "system:"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PromptTemplateStore:
    """TemplateRepository を薄く包んだ ViewModel 的ストア。"""

    def __init__(self, repository: TemplateRepository):
        self._repo = repository
        self._templates: List[PromptTemplate] = self._repo.load_templates()

    def list_templates(self, *, include_system: bool = False) -> List[PromptTemplate]:
        if include_system:
            return list(self._templates)
        return [tpl for tpl in self._templates if not self._is_system_template(tpl)]

    def create_template(self, title: str, body: str) -> PromptTemplate:
        title = title.strip()
        if not title:
            raise ValueError("テンプレート名を入力してください。")
        now = _now()
        tpl = PromptTemplate(
            id=uuid.uuid4().hex,
            title=title,
            body=body.strip(),
            created_at=now,
            updated_at=now,
        )
        self._templates.append(tpl)
        self._persist()
        return tpl

    def update_template(self, template_id: str, title: str, body: str) -> PromptTemplate:
        template = self._find(template_id)
        title = title.strip()
        if not title:
            raise ValueError("テンプレート名を入力してください。")
        template.title = title
        template.body = body.strip()
        template.updated_at = _now()
        self._persist()
        return template

    def delete_template(self, template_id: str) -> None:
        before = len(self._templates)
        self._templates = [tpl for tpl in self._templates if tpl.id != template_id]
        if len(self._templates) == before:
            raise ValueError("テンプレートが見つかりません。")
        self._persist()

    def upsert_system_template(
        self,
        template_id: str,
        title: str,
        body: str,
        *,
        overwrite: bool = False,
    ) -> PromptTemplate:
        """システム用テンプレートを ID 指定で登録/更新する。"""
        now = _now()
        template = PromptTemplate(
            id=f"{SYSTEM_TEMPLATE_PREFIX}{template_id}" if not template_id.startswith(SYSTEM_TEMPLATE_PREFIX) else template_id,
            title=title,
            body=body,
            created_at=now,
            updated_at=now,
        )
        for idx, existing in enumerate(self._templates):
            if existing.id == template.id:
                if overwrite:
                    template.created_at = existing.created_at
                    self._templates[idx] = template
                    self._persist()
                    return template
                return existing
        self._templates.append(template)
        self._persist()
        return template

    # ---- internals ----
    def _persist(self) -> None:
        self._repo.save_templates(self._templates)

    def _find(self, template_id: str) -> PromptTemplate:
        for tpl in self._templates:
            if tpl.id == template_id:
                return tpl
        raise ValueError("テンプレートが見つかりません。")

    @staticmethod
    def _is_system_template(template: PromptTemplate) -> bool:
        return template.id.startswith(SYSTEM_TEMPLATE_PREFIX)


