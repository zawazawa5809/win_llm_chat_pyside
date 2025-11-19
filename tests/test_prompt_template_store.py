from pathlib import Path
from typing import List

import pytest

from win_llm_chat_pyside.models import PromptTemplate
from win_llm_chat_pyside.features.prompts.prompt_repository import TemplateRepository
from win_llm_chat_pyside.features.prompts.prompt_template_store import PromptTemplateStore


def _titles(templates: List[PromptTemplate]) -> List[str]:
    return [tpl.title for tpl in templates]


def test_store_creates_and_persists_template(tmp_path: Path):
    repo = TemplateRepository(tmp_path)
    store = PromptTemplateStore(repo)

    store.create_template("Daily standup", "Summarize blockers")

    # reload to ensure persistence
    store = PromptTemplateStore(repo)
    templates = store.list_templates()
    assert len(templates) == 1
    assert templates[0].body == "Summarize blockers"


def test_store_update_edits_existing_template(tmp_path: Path):
    repo = TemplateRepository(tmp_path)
    store = PromptTemplateStore(repo)
    tpl = store.create_template("Greeting", "Hello")

    updated = store.update_template(tpl.id, "Greeting v2", "Hello again")
    assert updated.title == "Greeting v2"

    templates = store.list_templates()
    assert templates[0].title == "Greeting v2"
    assert templates[0].body == "Hello again"


def test_store_delete_removes_template(tmp_path: Path):
    repo = TemplateRepository(tmp_path)
    store = PromptTemplateStore(repo)
    tpl = store.create_template("To remove", "body")

    store.delete_template(tpl.id)
    assert store.list_templates() == []


def test_store_rejects_empty_title(tmp_path: Path):
    repo = TemplateRepository(tmp_path)
    store = PromptTemplateStore(repo)

    with pytest.raises(ValueError):
        store.create_template("", "body")


def test_system_templates_hidden_from_user_list(tmp_path: Path):
    repo = TemplateRepository(tmp_path)
    store = PromptTemplateStore(repo)

    tpl = store.upsert_system_template("file-summary-v1", "[System] Summary", "body")

    assert store.list_templates() == []
    all_templates = store.list_templates(include_system=True)
    assert len(all_templates) == 1
    assert all_templates[0].id == tpl.id


def test_system_template_overwrite_flag(tmp_path: Path):
    repo = TemplateRepository(tmp_path)
    store = PromptTemplateStore(repo)

    store.upsert_system_template("file-summary-v1", "[System] Summary", "body v1")
    tpl = store.upsert_system_template("file-summary-v1", "[System] Summary", "body v2")
    assert tpl.body == "body v1"

    tpl = store.upsert_system_template("file-summary-v1", "[System] Summary", "body v3", overwrite=True)
    assert tpl.body == "body v3"


