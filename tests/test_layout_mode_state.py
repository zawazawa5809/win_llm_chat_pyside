from win_llm_chat_pyside.core.config import Config
from win_llm_chat_pyside.models.layout_mode import LayoutMode
from win_llm_chat_pyside.features.chat.layout_mode_state import LayoutModeState


def test_layout_mode_state_reads_config_value():
    cfg = Config(layout_mode=LayoutMode.COMPACT.value)
    state = LayoutModeState(cfg)

    assert state.mode is LayoutMode.COMPACT


def test_layout_mode_state_set_mode_updates_config():
    cfg = Config(layout_mode=LayoutMode.FOCUSED.value)
    state = LayoutModeState(cfg)

    state.set_mode(LayoutMode.COMPACT)

    assert cfg.layout_mode == LayoutMode.COMPACT.value
    assert state.mode is LayoutMode.COMPACT


def test_layout_mode_state_toggle_cycles_between_modes():
    cfg = Config(layout_mode=LayoutMode.FOCUSED.value)
    state = LayoutModeState(cfg)

    first = state.toggle()
    second = state.toggle()

    assert first is LayoutMode.COMPACT
    assert second is LayoutMode.FOCUSED
    assert cfg.layout_mode == LayoutMode.FOCUSED.value


