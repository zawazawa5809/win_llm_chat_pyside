from datetime import datetime, timezone
from pathlib import Path

from src.win_llm_chat_pyside.models import PromptTemplate, RoleProfile
from src.win_llm_chat_pyside.prompt_repository import (
    TemplateRepository,
    RoleProfileRepository,
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def test_template_repository_roundtrip(tmp_path: Path):
    repo = TemplateRepository(tmp_path)
    template = PromptTemplate(
        id="tmpl-1",
        title="Warm greet",
        body="You are kind.",
        created_at=_ts(),
        updated_at=_ts(),
    )

    repo.save_templates([template])
    loaded = repo.load_templates()

    assert len(loaded) == 1
    assert loaded[0].title == "Warm greet"
    assert loaded[0].body == "You are kind."


def test_template_repository_returns_empty_on_invalid_json(tmp_path: Path):
    repo = TemplateRepository(tmp_path)
    file_path = tmp_path / "templates.json"
    file_path.write_text("{ invalid", encoding="utf-8")

    loaded = repo.load_templates()
    assert loaded == []


def test_role_profile_repository_roundtrip(tmp_path: Path):
    repo = RoleProfileRepository(tmp_path)
    profile = RoleProfile(
        id="role-1",
        name="Auditor",
        system_prompt="You audit.",
        is_default=False,
        created_at=_ts(),
        updated_at=_ts(),
    )

    repo.save_profiles([profile])
    loaded = repo.load_profiles()

    assert len(loaded) == 1
    assert loaded[0].name == "Auditor"
    assert loaded[0].system_prompt == "You audit."


def test_role_profile_repository_returns_empty_on_invalid_json(tmp_path: Path):
    repo = RoleProfileRepository(tmp_path)
    file_path = tmp_path / "role_profiles.json"
    file_path.write_text("{ invalid", encoding="utf-8")

    loaded = repo.load_profiles()
    assert loaded == []

