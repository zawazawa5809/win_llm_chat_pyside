"""
セッション作成・役割プロファイル選択ダイアログ。
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from win_llm_chat_pyside.models import RoleProfile


class SessionCreateDialog(QDialog):
    """セッション名と役割プロファイルの選択ダイアログ。"""

    def __init__(self, profiles: List[RoleProfile], parent=None):
        super().__init__(parent)
        self.setWindowTitle("新規セッション")
        self.resize(360, 160)
        self._profiles = profiles
        self._name_field = QLineEdit()
        self._profile_combo = QComboBox()
        self._populate_profiles()

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("セッション名 (任意):", self._name_field)
        form.addRow("役割プロファイル:", self._profile_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_profiles(self) -> None:
        self._profile_combo.addItem("選択しない", None)
        for profile in self._profiles:
            label = f"{profile.name} (既定)" if profile.is_default else profile.name
            self._profile_combo.addItem(label, profile.id)
        default_index = 0
        for idx in range(1, self._profile_combo.count()):
            if self._profile_combo.itemData(idx) is None:
                continue
            profile_id = self._profile_combo.itemData(idx)
            profile = next((p for p in self._profiles if p.id == profile_id), None)
            if profile and profile.is_default:
                default_index = idx
                break
        self._profile_combo.setCurrentIndex(default_index)

    def get_values(self) -> tuple[str, Optional[str]]:
        name = self._name_field.text().strip()
        profile_id = self._profile_combo.currentData()
        return name, profile_id


class RoleProfileSelectorDialog(QDialog):
    """既存セッション用の役割プロファイル選択ダイアログ。"""

    def __init__(
        self,
        profiles: List[RoleProfile],
        current_profile_id: Optional[str],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("役割プロファイルを切り替え")
        self.resize(320, 140)
        self._profiles = profiles
        self._combo = QComboBox()
        self._populate_profiles(current_profile_id)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("役割プロファイル:", self._combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_profiles(self, current_profile_id: Optional[str]) -> None:
        self._combo.addItem("選択しない", None)
        for profile in self._profiles:
            label = f"{profile.name} (既定)" if profile.is_default else profile.name
            self._combo.addItem(label, profile.id)
            if current_profile_id and profile.id == current_profile_id:
                self._combo.setCurrentIndex(self._combo.count() - 1)

    def get_selected_profile_id(self) -> Optional[str]:
        return self._combo.currentData()

