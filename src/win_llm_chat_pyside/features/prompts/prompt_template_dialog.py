"""
PySide6 ダイアログ: プロンプトテンプレート管理 UI。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QLineEdit,
)

from win_llm_chat_pyside.models import PromptTemplate
from win_llm_chat_pyside.features.prompts.prompt_template_store import PromptTemplateStore
from win_llm_chat_pyside.core.app_logger import app_logger


class PromptTemplateManagerDialog(QDialog):
    """テンプレート一覧の CRUD を提供する管理ダイアログ。"""

    def __init__(self, store: PromptTemplateStore, parent=None):
        super().__init__(parent)
        self.setWindowTitle("プロンプトテンプレート")
        self.resize(520, 360)
        self._store = store
        self._list = QListWidget()
        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)

        self._add_button = QPushButton("追加")
        self._edit_button = QPushButton("編集")
        self._delete_button = QPushButton("削除")
        self._close_button = QPushButton("閉じる")

        self._setup_layout()
        self._bind_events()
        self._refresh_list()

    def _setup_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("テンプレート一覧"))
        layout.addWidget(self._list, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._add_button)
        btn_row.addWidget(self._edit_button)
        btn_row.addWidget(self._delete_button)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        layout.addWidget(QLabel("本文プレビュー"))
        layout.addWidget(self._preview, stretch=2)

        layout.addWidget(self._close_button, alignment=Qt.AlignRight)

    def _bind_events(self) -> None:
        self._list.itemSelectionChanged.connect(self._update_preview)
        self._list.itemDoubleClicked.connect(lambda _: self._edit_selected())
        self._add_button.clicked.connect(self._add_template)
        self._edit_button.clicked.connect(self._edit_selected)
        self._delete_button.clicked.connect(self._delete_selected)
        self._close_button.clicked.connect(self.accept)

    def _refresh_list(self) -> None:
        self._list.clear()
        for template in self._store.list_templates():
            item = QListWidgetItem(template.title)
            item.setData(Qt.UserRole, template.id)
            self._list.addItem(item)
        self._preview.clear()

    def _handle_store_error(self, action: str, exc: Exception) -> None:
        try:
            app_logger.error(
                "prompt.templates.store_error",
                {"action": action, "error": str(exc)},
            )
        except Exception:
            pass
        QMessageBox.critical(self, "プロンプトテンプレート", f"{action}に失敗しました。\n{exc}")

    def _current_template(self) -> PromptTemplate | None:
        current = self._list.currentItem()
        if not current:
            return None
        template_id = current.data(Qt.UserRole)
        for tpl in self._store.list_templates():
            if tpl.id == template_id:
                return tpl
        return None

    def _add_template(self) -> None:
        editor = TemplateEditDialog(self)
        if editor.exec() == QDialog.Accepted:
            title, body = editor.get_values()
            try:
                self._store.create_template(title, body)
                self._refresh_list()
            except ValueError as exc:
                QMessageBox.warning(self, "入力エラー", str(exc))
            except Exception as exc:
                self._handle_store_error("テンプレートの追加", exc)

    def _edit_selected(self) -> None:
        template = self._current_template()
        if not template:
            QMessageBox.information(self, "編集", "編集するテンプレートを選択してください。")
            return
        editor = TemplateEditDialog(self, template)
        if editor.exec() == QDialog.Accepted:
            title, body = editor.get_values()
            try:
                self._store.update_template(template.id, title, body)
                self._refresh_list()
            except ValueError as exc:
                QMessageBox.warning(self, "入力エラー", str(exc))
            except Exception as exc:
                self._handle_store_error("テンプレートの更新", exc)

    def _delete_selected(self) -> None:
        template = self._current_template()
        if not template:
            QMessageBox.information(self, "削除", "削除するテンプレートを選択してください。")
            return
        confirm = QMessageBox.question(
            self,
            "テンプレート削除",
            f"「{template.title}」を削除しますか？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self._store.delete_template(template.id)
            self._refresh_list()
        except ValueError as exc:
            QMessageBox.warning(self, "削除エラー", str(exc))
        except Exception as exc:
            self._handle_store_error("テンプレートの削除", exc)

    def _update_preview(self) -> None:
        template = self._current_template()
        if not template:
            self._preview.clear()
            return
        self._preview.setPlainText(template.body)


class TemplateEditDialog(QDialog):
    """テンプレートの追加/編集用サブダイアログ。"""

    def __init__(self, parent=None, template: PromptTemplate | None = None):
        super().__init__(parent)
        self.setWindowTitle("テンプレートを編集")
        self.resize(420, 320)
        self._title_field = QLineEdit()
        self._body_field = QPlainTextEdit()

        if template:
            self._title_field.setText(template.title)
            self._body_field.setPlainText(template.body)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("タイトル:", self._title_field)
        layout.addLayout(form)
        layout.addWidget(QLabel("本文 (Markdown 可):"))
        layout.addWidget(self._body_field, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> tuple[str, str]:
        return self._title_field.text(), self._body_field.toPlainText()


