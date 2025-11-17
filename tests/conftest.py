"""Ensure src/ is importable for all tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture(scope="session")
def qt_app():
    """Provide a shared QApplication instance for widget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

