"""
ショートカットキーのヘルプダイアログ。
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QDialogButtonBox,
    QLineEdit,
)

from win_llm_chat_pyside.ui.shortcut_registry import ShortcutRegistry, ShortcutMeta


class ShortcutHelpDialog(QDialog):
    """ショートカットキーのヘルプを表示するダイアログ。"""

    def __init__(self, registry: ShortcutRegistry, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ショートカットキー")
        self.setMinimumWidth(520)
        self.setMinimumHeight(420)
        self._registry = registry
        self._filter_text = ""

        layout = QVBoxLayout(self)

        label = QLabel("利用可能なショートカットキー:")
        layout.addWidget(label)

        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText("キーワードでフィルタ...")
        self._filter_input.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self._filter_input)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        layout.addWidget(self._text_edit)
        self._refresh_text()

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _on_filter_changed(self, text: str) -> None:
        self._filter_text = text.strip()
        self._refresh_text()

    def _refresh_text(self) -> None:
        self._text_edit.setPlainText(self._generate_help_text())

    def _generate_help_text(self) -> str:
        """登録済みショートカットからヘルプテキストを生成する。"""

        entries = self._registry.all()
        if self._filter_text:
            needle = self._filter_text.casefold()
            entries = [
                entry
                for entry in entries
                if needle in entry.key.casefold()
                or needle in entry.description.casefold()
                or needle in entry.category.casefold()
            ]
        if not entries:
            return "登録されたショートカットが見つかりません。"

        lines: list[str] = []
        current_category = None
        for entry in entries:
            if entry.category != current_category:
                current_category = entry.category
                lines.append(f"【{current_category}】")
            lines.append(self._format_entry(entry))
        return "\n".join(lines)

    @staticmethod
    def _format_entry(entry: ShortcutMeta) -> str:
        scope = " (グローバル)" if entry.scope == "global" else ""
        padded_key = entry.key.ljust(18)
        return f"  {padded_key} {entry.description}{scope}"

