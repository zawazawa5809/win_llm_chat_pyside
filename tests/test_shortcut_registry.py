from win_llm_chat_pyside.shortcut_registry import ShortcutRegistry


def test_register_and_list_shortcuts():
    registry = ShortcutRegistry()

    registry.register(key="Ctrl+F", description="セッション内検索", category="検索")
    registry.register(key="F1", description="ショートカット一覧", category="ヘルプ")

    shortcuts = registry.all()

    assert len(shortcuts) == 2
    assert shortcuts[0].key == "Ctrl+F"
    assert shortcuts[1].description == "ショートカット一覧"


def test_duplicate_registration_with_different_description_raises():
    registry = ShortcutRegistry()
    registry.register(key="Ctrl+F", description="セッション内検索", category="検索")

    try:
        registry.register(key=" Ctrl+F ", description="別の意味", category="検索")
    except ValueError as exc:
        assert "Ctrl+F" in str(exc)
    else:
        raise AssertionError("duplicate registration should raise")


def test_unregister_removes_shortcut():
    registry = ShortcutRegistry()
    registry.register(key="Ctrl+Enter", description="送信", category="チャット")

    registry.unregister("Ctrl+Enter")

    assert registry.all() == []


