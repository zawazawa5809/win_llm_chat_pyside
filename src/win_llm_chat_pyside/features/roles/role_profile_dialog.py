"""
PySide6 ダイアログ: 役割プロファイル管理 UI。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
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
    QLineEdit,
    QVBoxLayout,
)

from win_llm_chat_pyside.models import RoleProfile
from win_llm_chat_pyside.features.roles.role_profile_store import RoleProfileStore
from win_llm_chat_pyside.core.app_logger import app_logger


class RoleProfileManagerDialog(QDialog):
    """役割プロファイルの追加/編集/削除/既定設定を提供するダイアログ。"""

    def __init__(self, store: RoleProfileStore, parent=None):
        super().__init__(parent)
        self.setWindowTitle("役割プロファイル")
        self.resize(560, 380)
        self._store = store
        self._list = QListWidget()
        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)

        self._add_button = QPushButton("追加")
        self._edit_button = QPushButton("編集")
        self._delete_button = QPushButton("削除")
        self._default_button = QPushButton("既定に設定")
        self._close_button = QPushButton("閉じる")

        self._setup_layout()
        self._bind_events()
        self._refresh_list()

    def _setup_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("役割プロファイル一覧"))
        layout.addWidget(self._list, stretch=1)

        button_row = QHBoxLayout()
        button_row.addWidget(self._add_button)
        button_row.addWidget(self._edit_button)
        button_row.addWidget(self._delete_button)
        button_row.addWidget(self._default_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        layout.addWidget(QLabel("system prompt プレビュー"))
        layout.addWidget(self._preview, stretch=2)

        layout.addWidget(self._close_button, alignment=Qt.AlignRight)

    def _bind_events(self) -> None:
        self._list.itemSelectionChanged.connect(self._update_preview)
        self._list.itemDoubleClicked.connect(lambda _: self._edit_selected())
        self._add_button.clicked.connect(self._add_profile)
        self._edit_button.clicked.connect(self._edit_selected)
        self._delete_button.clicked.connect(self._delete_selected)
        self._default_button.clicked.connect(self._set_default_selected)
        self._close_button.clicked.connect(self.accept)

    def _refresh_list(self) -> None:
        self._list.clear()
        for profile in self._store.list_profiles():
            item = QListWidgetItem(self._format_label(profile))
            item.setData(Qt.UserRole, profile.id)
            self._list.addItem(item)
        self._preview.clear()

    def _handle_store_error(self, action: str, exc: Exception) -> None:
        try:
            app_logger.error(
                "prompt.role_profiles.store_error",
                {"action": action, "error": str(exc)},
            )
        except Exception:
            pass
        QMessageBox.critical(self, "役割プロファイル", f"{action}に失敗しました。\n{exc}")

    @staticmethod
    def _format_label(profile: RoleProfile) -> str:
        suffix = " (既定)" if profile.is_default else ""
        return f"{profile.name}{suffix}"

    def _current_profile(self) -> Optional[RoleProfile]:
        current = self._list.currentItem()
        if not current:
            return None
        profile_id = current.data(Qt.UserRole)
        return self._store.get_profile(profile_id)

    def _add_profile(self) -> None:
        editor = RoleProfileEditDialog(self)
        if editor.exec() != QDialog.Accepted:
            return
        name, prompt, make_default = editor.get_values()
        try:
            self._store.create_profile(name, prompt, make_default=make_default)
            self._refresh_list()
        except ValueError as exc:
            QMessageBox.warning(self, "入力エラー", str(exc))
        except Exception as exc:
            self._handle_store_error("役割プロファイルの追加", exc)

    def _edit_selected(self) -> None:
        profile = self._current_profile()
        if not profile:
            QMessageBox.information(self, "編集", "編集するプロファイルを選択してください。")
            return
        editor = RoleProfileEditDialog(self, profile)
        if editor.exec() != QDialog.Accepted:
            return
        name, prompt, make_default = editor.get_values()
        try:
            self._store.update_profile(profile.id, name, prompt, make_default=make_default)
            self._refresh_list()
        except ValueError as exc:
            QMessageBox.warning(self, "入力エラー", str(exc))
        except Exception as exc:
            self._handle_store_error("役割プロファイルの更新", exc)

    def _delete_selected(self) -> None:
        profile = self._current_profile()
        if not profile:
            QMessageBox.information(self, "削除", "削除するプロファイルを選択してください。")
            return
        confirm = QMessageBox.question(
            self,
            "プロファイル削除",
            f"「{profile.name}」を削除しますか？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self._store.delete_profile(profile.id)
            self._refresh_list()
        except ValueError as exc:
            QMessageBox.warning(self, "削除エラー", str(exc))
        except Exception as exc:
            self._handle_store_error("役割プロファイルの削除", exc)

    def _set_default_selected(self) -> None:
        profile = self._current_profile()
        if not profile:
            QMessageBox.information(self, "既定", "既定に設定するプロファイルを選択してください。")
            return
        try:
            self._store.set_default(profile.id)
            self._refresh_list()
        except ValueError as exc:
            QMessageBox.warning(self, "既定設定エラー", str(exc))
        except Exception as exc:
            self._handle_store_error("既定設定", exc)

    def _update_preview(self) -> None:
        profile = self._current_profile()
        if not profile:
            self._preview.clear()
            return
        self._preview.setPlainText(profile.system_prompt)


class RoleProfileEditDialog(QDialog):
    """役割プロファイルの編集/追加用ダイアログ。"""

    def __init__(self, parent=None, profile: Optional[RoleProfile] = None):
        super().__init__(parent)
        self.setWindowTitle("役割プロファイルを編集")
        self.resize(450, 360)
        self._name_field = QLineEdit()
        self._prompt_field = QPlainTextEdit()
        self._default_checkbox = QCheckBox("既定に設定")

        if profile:
            self._name_field.setText(profile.name)
            self._prompt_field.setPlainText(profile.system_prompt)
            self._default_checkbox.setChecked(profile.is_default)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("名前:", self._name_field)
        layout.addLayout(form)
        layout.addWidget(QLabel("system prompt (Markdown 可):"))
        layout.addWidget(self._prompt_field, stretch=1)
        layout.addWidget(self._default_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> tuple[str, str, bool]:
        return (
            self._name_field.text(),
            self._prompt_field.toPlainText(),
            self._default_checkbox.isChecked(),
        )

