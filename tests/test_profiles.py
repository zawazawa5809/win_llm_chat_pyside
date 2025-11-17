import json
from pathlib import Path
from typing import Any

from win_llm_chat_pyside import config as cfg_mod
from win_llm_chat_pyside.factory import create_llm_client
from win_llm_chat_pyside.client import OpenAiCompatibleClient, OllamaClient


def test_migration_single_to_profiles(tmp_path: Path, monkeypatch: Any):
    # Arrange: 旧スキーマの設定を書き出す
    conf_path = tmp_path / "config.json"
    data = {
        "base_url": "http://localhost:11434",
        "model": "gemma3:4b",
        "api_key": "secret",
    }
    conf_path.write_text(json.dumps(data), encoding="utf-8")

    # get_config_path を差し替えて当該ファイルを指す
    monkeypatch.setattr(cfg_mod, "get_config_path", lambda: conf_path)

    # Act
    cfg = cfg_mod.load_config()

    # Assert: profiles[0] が生成され current が設定される
    assert cfg.profiles, "profiles が生成されていること"
    assert cfg.current_profile_name == "default"
    p0 = cfg.profiles[0]
    assert p0.name == "default"
    assert p0.type == "openai"
    assert p0.base_url == "http://localhost:11434"
    assert p0.model == "gemma3:4b"
    assert p0.api_key == "secret"


def test_factory_creates_expected_client_types():
    p_openai = cfg_mod.Profile(
        name="a", type="openai", base_url="http://x", model="g"
    )
    client1 = create_llm_client(p_openai, 5000, 30000)
    assert isinstance(client1, OpenAiCompatibleClient)

    p_ollama = cfg_mod.Profile(
        name="b", type="ollama", base_url="http://x", model="g"
    )
    client2 = create_llm_client(p_ollama, 5000, 30000)
    assert isinstance(client2, OllamaClient)


