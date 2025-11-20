from win_llm_chat_pyside.core.config import Config, _config_from_dict
from win_llm_chat_pyside.models.layout_mode import LayoutMode



def test_config_defaults_to_not_always_on_top():
    cfg = Config()
    assert cfg.always_on_top is False


def test_config_defaults_window_geometry_none():
    cfg = Config()
    assert cfg.window_geometry is None


def test_config_migration_sets_default_when_missing():
    cfg = _config_from_dict({})
    assert cfg.always_on_top is False
    assert cfg.start_minimized_to_tray is False


def test_config_migration_respects_existing_always_on_top():
    cfg = _config_from_dict({"always_on_top": True})
    assert cfg.always_on_top is True


def test_config_migration_preserves_window_geometry():
    cfg = _config_from_dict({"window_geometry": "Z2VvbWV0cnk="})
    assert cfg.window_geometry == "Z2VvbWV0cnk="


def test_config_migration_respects_existing_start_minimized_to_tray():
    cfg = _config_from_dict({"start_minimized_to_tray": True})
    assert cfg.start_minimized_to_tray is True


def test_config_defaults_to_focused_layout_mode():
    cfg = Config()
    assert cfg.layout_mode == LayoutMode.FOCUSED.value


def test_config_migration_preserves_layout_mode():
    cfg = _config_from_dict({"layout_mode": LayoutMode.COMPACT.value})
    assert cfg.layout_mode == LayoutMode.COMPACT.value


def test_config_migration_invalid_layout_mode_falls_back():
    cfg = _config_from_dict({"layout_mode": "unknown"})
    assert cfg.layout_mode == LayoutMode.FOCUSED.value


def test_config_defaults_clipboard_limits():
    cfg = Config()
    assert cfg.clipboard_image_max_bytes == 2_000_000
    assert cfg.clipboard_image_max_total_pixels == 8_000_000


def test_config_migration_respects_clipboard_settings():
    cfg = _config_from_dict(
        {
            "clipboard_image_max_bytes": 1234,
            "clipboard_image_max_total_pixels": 9876,
            "clipboard_image_dir": "/tmp/example",
        }
    )
    assert cfg.clipboard_image_max_bytes == 1234
    assert cfg.clipboard_image_max_total_pixels == 9876
    assert cfg.clipboard_image_dir == "/tmp/example"


def test_config_defaults_main_and_attachment_tabs():
    cfg = Config()
    assert cfg.ui_main_selected_tab == "chat"


def test_config_defaults_attachment_send_limits():
    cfg = Config()
    assert cfg.attachment_send_max_chars == 20_000
    assert cfg.attachment_send_truncate_notice_enabled is True


def test_config_migration_attachment_send_limits():
    cfg = _config_from_dict(
        {
            "attachment_send_max_chars": 1234,
            "attachment_send_truncate_notice_enabled": False,
        }
    )
    assert cfg.attachment_send_max_chars == 1234
    assert cfg.attachment_send_truncate_notice_enabled is False
