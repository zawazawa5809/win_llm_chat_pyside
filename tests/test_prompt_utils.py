from src.win_llm_chat_pyside.prompt_utils import merge_template_text


def test_merge_template_text_replaces_when_empty():
    result = merge_template_text("", "Hello world")
    assert result == "Hello world"


def test_merge_template_text_appends_with_blank_line():
    result = merge_template_text("Existing text", "New body")
    assert result == "Existing text\n\nNew body"


def test_merge_template_text_handles_whitespace():
    result = merge_template_text("  existing  ", "  body  ")
    assert result == "existing\n\nbody"

