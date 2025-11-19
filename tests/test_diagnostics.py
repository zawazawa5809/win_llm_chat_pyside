from win_llm_chat_pyside.core.config import Config, Profile
from win_llm_chat_pyside.ui.dialogs.diagnostics_dialog import DiagnosticsInfoProvider


def test_diagnostics_basic_fields_and_profile():
    cfg = Config()
    cfg.profiles = [Profile(name="p1", type="openai", base_url="http://x", model="g")]
    cfg.current_profile_name = "p1"

    provider = DiagnosticsInfoProvider(cfg)
    info = provider.collect()

    v = info.values
    assert "app_version" in v
    assert "python_version" in v
    assert "os" in v
    assert v["profile_name"] == "p1"
    assert v["profile_type"] == "openai"
    # 既定では詳細パスは含まれない
    assert "data_dir" not in v
    assert "logs_dir" not in v


def test_diagnostics_env_details_flag_adds_paths():
    cfg = Config()
    cfg.diagnostics_show_env_details = True

    provider = DiagnosticsInfoProvider(cfg)
    info = provider.collect()

    assert "data_dir" in info.values
    assert "logs_dir" in info.values
    assert info.values["data_dir"]
    assert info.values["logs_dir"]


def test_diagnostics_format_text_contains_keys():
    cfg = Config()
    provider = DiagnosticsInfoProvider(cfg)
    info = provider.collect()

    text = provider.format_text(info)
    # 代表キーが含まれていること
    assert "app_version" in text
    assert "python_version" in text


