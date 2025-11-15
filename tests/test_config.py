from win_llm_chat_pyside.config import Config, _config_from_dict


def test_config_defaults_to_not_always_on_top():
    cfg = Config()
    assert cfg.always_on_top is False


def test_config_migration_sets_default_when_missing():
    cfg = _config_from_dict({})
    assert cfg.always_on_top is False


def test_config_migration_respects_existing_always_on_top():
    cfg = _config_from_dict({"always_on_top": True})
    assert cfg.always_on_top is True


