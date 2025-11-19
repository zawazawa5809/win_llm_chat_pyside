import json
from pathlib import Path
from typing import Any

from win_llm_chat_pyside.core import config as cfg_mod
from win_llm_chat_pyside import profile_repository as repo


def test_repository_load_migrates_from_single_schema(tmp_path: Path, monkeypatch: Any):
    # Arrange: 旧スキーマを書き出し
    conf_path = tmp_path / "config.json"
    single = {"base_url": "http://localhost:11434", "model": "gemma3:4b", "api_key": "secret"}
    conf_path.write_text(json.dumps(single), encoding="utf-8")
    monkeypatch.setattr(cfg_mod, "get_config_path", lambda: conf_path)

    # Act: Repository を経由してロード
    profiles, current = repo.load()

    # Assert: profiles[0] が生成され current が設定される
    assert profiles and isinstance(profiles, list)
    assert current == "default"
    p0 = profiles[0]
    assert p0.name == "default"
    assert p0.type in ("openai", "ollama")
    assert p0.base_url == "http://localhost:11434"
    assert p0.model == "gemma3:4b"
    assert p0.api_key == "secret"


def test_repository_save_and_read_back(tmp_path: Path, monkeypatch: Any):
    # Arrange: 空ファイルパスを指すようにする
    conf_path = tmp_path / "config.json"
    monkeypatch.setattr(cfg_mod, "get_config_path", lambda: conf_path)

    from win_llm_chat_pyside.core.config import Profile
    profiles = [Profile(name="a", type="openai", base_url="http://x", model="m")]

    # Act: 保存 → Config 経由で読み戻す
    repo.save(profiles, current="a")
    loaded_cfg = cfg_mod.load_config()

    # Assert
    assert loaded_cfg.current_profile_name == "a"
    assert loaded_cfg.profiles and loaded_cfg.profiles[0].name == "a"


def test_save_full_config_preserves_other_settings(tmp_path, monkeypatch):
    conf_path = tmp_path / "config.json"
    monkeypatch.setattr(cfg_mod, "get_config_path", lambda: conf_path)
    # 任意の設定を上書きして保存
    cfg = cfg_mod.Config()
    cfg.ui_markdown_font_size_pt = 13
    cfg.history_enabled = False
    cfg.profiles = [cfg_mod.Profile(name="p", type="openai", base_url="http://x", model="m")]
    cfg.current_profile_name = "p"
    repo.save_full_config(cfg)

    loaded = cfg_mod.load_config()
    assert loaded.ui_markdown_font_size_pt == 13
    assert loaded.history_enabled is False
    assert loaded.current_profile_name == "p"


