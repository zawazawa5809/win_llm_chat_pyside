from PySide6.QtWidgets import QWidget

from win_llm_chat_pyside.models.layout_mode import LayoutMode
from win_llm_chat_pyside.ui.main_layout import MainLayoutContainer


def _create_container():
    sidebar = QWidget()
    content = QWidget()
    container = MainLayoutContainer(sidebar, content)
    container.resize(1200, 800)
    return container


def test_focus_mode_allocates_sidebar_width(qt_app):
    container = _create_container()

    container.set_layout_mode(LayoutMode.FOCUSED)

    assert container.sidebar_width() >= container.DEFAULT_SIDEBAR_WIDTH


def test_compact_mode_collapses_sidebar(qt_app):
    container = _create_container()
    container.set_layout_mode(LayoutMode.FOCUSED)

    container.set_layout_mode(LayoutMode.COMPACT)

    assert container.sidebar_width() <= container.COMPACT_SIDEBAR_WIDTH + 1


def test_toggling_back_restores_previous_width(qt_app):
    container = _create_container()
    container.set_layout_mode(LayoutMode.FOCUSED)
    initial_width = container.sidebar_width()

    container.set_layout_mode(LayoutMode.COMPACT)
    container.set_layout_mode(LayoutMode.FOCUSED)

    assert container.sidebar_width() == initial_width


