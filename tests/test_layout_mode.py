from win_llm_chat_pyside.models.layout_mode import LayoutMode


def test_from_value_returns_expected_enum():
    assert LayoutMode.from_value("focused") is LayoutMode.FOCUSED
    assert LayoutMode.from_value("compact") is LayoutMode.COMPACT


def test_from_value_falls_back_for_invalid_input():
    assert LayoutMode.from_value("invalid") is LayoutMode.FOCUSED
    assert LayoutMode.from_value(None) is LayoutMode.FOCUSED


