from pathlib import Path

import pytest
from src.win_llm_chat_pyside.prompt_repository import RoleProfileRepository
from src.win_llm_chat_pyside.role_profile_store import RoleProfileStore


def test_create_profile_sets_default_when_first(tmp_path: Path):
    repo = RoleProfileRepository(tmp_path)
    store = RoleProfileStore(repo)

    profile = store.create_profile("Default", "You act politely.")

    assert profile.is_default is True
    stored = store.list_profiles()
    assert stored[0].name == "Default"


def test_update_profile_switches_default(tmp_path: Path):
    repo = RoleProfileRepository(tmp_path)
    store = RoleProfileStore(repo)
    a = store.create_profile("A", "prompt A")
    b = store.create_profile("B", "prompt B")

    updated = store.update_profile(b.id, "B*", "prompt B*", make_default=True)

    assert updated.is_default is True
    refreshed = store.list_profiles()
    assert any(p.id == b.id and p.is_default for p in refreshed)
    assert any(p.id == a.id and not p.is_default for p in refreshed)


def test_delete_profile_reassigns_default(tmp_path: Path):
    repo = RoleProfileRepository(tmp_path)
    store = RoleProfileStore(repo)
    a = store.create_profile("A", "prompt A")
    b = store.create_profile("B", "prompt B", make_default=False)
    store.set_default(b.id)

    store.delete_profile(b.id)

    remaining = store.list_profiles()
    assert len(remaining) == 1
    assert remaining[0].id == a.id
    assert remaining[0].is_default is True


def test_create_profile_rejects_empty_name(tmp_path: Path):
    repo = RoleProfileRepository(tmp_path)
    store = RoleProfileStore(repo)

    with pytest.raises(ValueError):
        store.create_profile("", "body")

