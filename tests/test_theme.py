from win_llm_chat_pyside.ui.styles.theme import ThemeRole, build_composer_styles, get_theme


def test_get_theme_returns_expected_color_tokens():
    theme = get_theme()

    assert theme.colors.chat_bg.startswith("#")
    assert theme.colors.sidebar_bg.startswith("#")
    assert theme.colors.bubble_user_bg.startswith("#")
    assert theme.colors.bubble_assistant_text.startswith("#")
    assert theme.typography.body_size > 0
    assert theme.spacing.sm > 0
    assert theme.spacing.bubble_padding > 0


def test_theme_role_members_cover_expected_roles():
    assert ThemeRole.CHAT.value == "chat"
    assert ThemeRole.SIDEBAR.value == "sidebar"
    assert ThemeRole.COMPOSER.value == "composer"
    assert ThemeRole.CHAT_BUBBLE_USER.value == "chat-bubble-user"
    assert ThemeRole.CHAT_META.value == "chat-meta"


def test_build_composer_styles_includes_required_css_tokens():
    theme = get_theme()
    styles = build_composer_styles(theme)
    assert "MessageComposerWidget" in styles
    assert theme.colors.composer_bg in styles

