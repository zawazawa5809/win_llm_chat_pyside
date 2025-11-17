---
permalink: /pyside6-theme-design-guide
title: "PySide6テーマ設計完全ガイド - 統一性と拡張性を両立する実装パターン"
summary: "PySide6アプリケーションで統一的なテーマシステムを構築する包括的ガイド。QPaletteベース設計、デザイントークン、ファクトリーパターンを活用し、機能追加時も一貫性を保つ実装方法を解説。"
tags:
  - "#pyside6"
  - "#qt6"
  - "#python"
  - "#gui"
  - "#theme-design"
  - "#design-system"
---

# PySide6テーマ設計完全ガイド - 統一性と拡張性を両立する実装パターン

## はじめに

PySide6でデスクトップアプリケーションを開発する際、多くの開発者が直面する課題がある。機能を追加するたびにUIデザインが不統一になり、ダークモードとライトモードの切り替えは複雑で、テーマのメンテナンスは困難を極める。これらの問題は、アプリケーションの成長とともに深刻化し、最終的にユーザー体験の低下を招く。

本記事では、これらの課題を根本的に解決するテーマ設計システムを提案する。QPalette（キューパレット）ベースの設計、ThemeManagerによる一元管理、デザイントークンシステムを組み合わせることで、統一的で美しいUI、簡単なテーマ切り替え、高い保守性を実現する方法を詳細に解説する。

## テーマ設計の基本概念

### QPaletteベース設計の必要性

QPaletteは、Qt/PySide6における色管理の中核となるクラスである。このクラスは、ウィジェットの各部分に対して論理的な色の役割（Color Role）を定義し、プラットフォームやテーマに依存しない色管理を可能にする。

従来のアプローチでは、スタイルシートに直接色を指定することが多い。しかし、この方法には重大な欠点がある。

```python
# ❌ 悪い例：直接色指定
widget.setStyleSheet("""
    QWidget {
        background-color: #232428;
        color: #ffffff;
    }
""")
```

このような直接指定は、テーマ切り替え時に全てのスタイルシートを更新する必要があり、保守性が著しく低下する。さらに、システムテーマとの親和性も失われ、プラットフォーム間の一貫性を保つことが困難になる。

対照的に、QPaletteベースの設計では、色を論理的な役割で管理する。

```python
# ✅ 良い例：palette()参照
widget.setStyleSheet("""
    QWidget {
        background-color: palette(window);
        color: palette(window-text);
    }
""")
```

この方法により、テーマ変更は単にQPaletteオブジェクトを切り替えるだけで完了し、全てのウィジェットが自動的に新しい配色に従う。

### QStyleSheetとpalette()参照

QStyleSheet（QSS）は、CSS-likeな記法でウィジェットのスタイルを定義できる強力な機能である。palette()関数を使用することで、QSSの中でもQPaletteの色を参照でき、動的なテーマ対応が可能になる。

QPaletteには以下の主要な色役割が定義されている：

| 色役割 | 用途 | 使用例 |
|--------|------|--------|
| Window | ウィンドウ背景 | メインウィンドウ、ダイアログ |
| WindowText | ラベル・静的テキスト | QLabel、タイトルバー |
| Base | 入力フィールド背景 | QLineEdit、QTextEdit |
| AlternateBase | 交互行背景 | QTableViewの偶数行 |
| Text | 入力フィールドのテキスト | エディタ内テキスト |
| Button | ボタン背景 | QPushButton |
| ButtonText | ボタンテキスト | ボタンラベル |
| Highlight | 選択背景 | 選択項目、フォーカス |
| HighlightedText | 選択テキスト | 選択時の文字色 |
| Mid | 区切り線・境界 | グリッド線、セパレータ |

### Fusionスタイルの役割

Fusionスタイルは、PySide6において特別な意味を持つ。これはクロスプラットフォーム対応の統一されたスタイルであり、特にダークモード実装において必須となる。

```python
from PySide6.QtWidgets import QApplication

app = QApplication([])
app.setStyle("Fusion")  # 必須：特にWindowsでダークモード実装時
```

Fusionスタイルを使用しない場合、特にWindowsプラットフォームでは、ネイティブスタイルがQPaletteの設定を完全に反映しない問題が発生する。これは、WindowsのネイティブスタイルがシステムテーマエンジンとQPaletteの間で競合を起こすためである。

## アーキテクチャ設計

### 階層型テーマシステム

効果的なテーマシステムは、以下の3層構造で設計される：

```
┌─────────────────────────────────────┐
│     アプリケーションレベル           │
│  (ThemeManager, 設定永続化, API)     │
├─────────────────────────────────────┤
│     コンポーネントレベル             │
│  (カスタムウィジェット, スタイル)    │
├─────────────────────────────────────┤
│     システムレベル                   │
│  (QPalette, QStyle, QStyleSheet)     │
└─────────────────────────────────────┘
```

各層は明確な責任を持つ：

- **システムレベル**：Qt/PySide6の基本機能を提供
- **コンポーネントレベル**：再利用可能なUI部品を実装
- **アプリケーションレベル**：テーマの管理と永続化を担当

### ThemeManagerの実装

ThemeManagerは、テーマシステムの中核となるコンポーネントである。シングルトンパターンを採用し、アプリケーション全体で一つのインスタンスのみが存在することを保証する。

```python
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import QObject, Signal, QSettings
from typing import Dict, Optional, ClassVar
import json
from pathlib import Path

class ThemeManager(QObject):
    """統一されたテーマ管理システム"""

    _instance: ClassVar[Optional['ThemeManager']] = None
    theme_changed = Signal(str)  # テーマ変更シグナル

    def __new__(cls, app: Optional[QApplication] = None):
        """シングルトンパターンの実装"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, app: Optional[QApplication] = None):
        """初期化（一度のみ実行）"""
        if hasattr(self, '_initialized'):
            return

        super().__init__()
        self.app = app or QApplication.instance()
        self.themes: Dict[str, Dict] = {}
        self.current_theme: Optional[str] = None
        self.settings = QSettings("MyCompany", "MyApp")
        self._initialized = True
        self._load_theme_definitions()
        self._restore_last_theme()

    def _load_theme_definitions(self):
        """テーマ定義をJSONから読み込み"""
        theme_dir = Path("themes")
        theme_dir.mkdir(exist_ok=True)

        # デフォルトテーマを作成
        self._create_default_themes()

        # カスタムテーマを読み込み
        for theme_file in theme_dir.glob("*.json"):
            try:
                with open(theme_file, 'r', encoding='utf-8') as f:
                    theme_data = json.load(f)
                    self.themes[theme_file.stem] = theme_data
            except (json.JSONDecodeError, IOError) as e:
                print(f"テーマ読み込みエラー {theme_file}: {e}")

    def _create_default_themes(self):
        """組み込みのデフォルトテーマを作成"""
        self.themes['dark'] = {
            'name': 'Dark Professional',
            'colors': {
                'window': '#232428',
                'window_text': '#eeeeee',
                'base': '#2b2d31',
                'alternate_base': '#33353a',
                'text': '#eeeeee',
                'button': '#2b2d31',
                'button_text': '#eeeeee',
                'highlight': '#2f6fff',
                'highlighted_text': '#ffffff',
                'mid': '#45474c',
                'shadow': '#121315',
                'light': '#58595e',
                'disabled_text': '#808080'
            },
            'dimensions': {
                'font_family': 'Segoe UI',
                'font_size': 10,
                'border_radius': 4,
                'padding': 6,
                'padding_large': 12,
                'min_button_height': 24
            }
        }

        self.themes['light'] = {
            'name': 'Light Clean',
            'colors': {
                'window': '#f4f5f6',
                'window_text': '#212121',
                'base': '#ffffff',
                'alternate_base': '#f0f1f3',
                'text': '#212121',
                'button': '#ffffff',
                'button_text': '#212121',
                'highlight': '#1866ff',
                'highlighted_text': '#ffffff',
                'mid': '#d0d2d6',
                'shadow': '#bdbfc4',
                'light': '#ffffff',
                'disabled_text': '#808080'
            },
            'dimensions': {
                'font_family': 'Segoe UI',
                'font_size': 10,
                'border_radius': 4,
                'padding': 6,
                'padding_large': 12,
                'min_button_height': 24
            }
        }

    def apply_theme(self, theme_name: str):
        """テーマを適用"""
        if theme_name not in self.themes:
            raise ValueError(f"Unknown theme: {theme_name}")

        # Fusionスタイルを強制（必須）
        self.app.setStyle("Fusion")

        # パレット生成と適用
        palette = self._create_palette(self.themes[theme_name])
        self.app.setPalette(palette)

        # グローバルスタイルシート適用
        qss = self._generate_qss(self.themes[theme_name])
        self.app.setStyleSheet(qss)

        # すべてのウィジェットを再描画
        self._repolish_widgets()

        # 状態を保存
        self.current_theme = theme_name
        self.settings.setValue("theme", theme_name)
        self.theme_changed.emit(theme_name)

    def _create_palette(self, theme: Dict) -> QPalette:
        """テーマ定義からQPaletteを生成"""
        palette = QPalette()

        # 色役割マッピング
        color_roles = {
            'window': QPalette.Window,
            'window_text': QPalette.WindowText,
            'base': QPalette.Base,
            'alternate_base': QPalette.AlternateBase,
            'text': QPalette.Text,
            'button': QPalette.Button,
            'button_text': QPalette.ButtonText,
            'highlight': QPalette.Highlight,
            'highlighted_text': QPalette.HighlightedText,
            'mid': QPalette.Mid,
            'shadow': QPalette.Shadow,
            'light': QPalette.Light
        }

        colors = theme.get('colors', {})
        for key, role in color_roles.items():
            if key in colors:
                palette.setColor(role, QColor(colors[key]))

        # 無効状態の色も設定
        if 'disabled_text' in colors:
            palette.setColor(QPalette.Disabled, QPalette.WindowText,
                           QColor(colors['disabled_text']))
            palette.setColor(QPalette.Disabled, QPalette.ButtonText,
                           QColor(colors['disabled_text']))
            palette.setColor(QPalette.Disabled, QPalette.Text,
                           QColor(colors['disabled_text']))

        return palette

    def _generate_qss(self, theme: Dict) -> str:
        """テーマ定義からQSSを生成"""
        dims = theme.get('dimensions', {})

        qss = f"""
        * {{
            font-family: '{dims.get('font_family', 'Segoe UI')}';
            font-size: {dims.get('font_size', 10)}px;
        }}

        QWidget {{
            background-color: palette(window);
            color: palette(window-text);
        }}

        /* 入力フィールド */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
            background-color: palette(base);
            color: palette(text);
            border: 1px solid palette(mid);
            border-radius: {dims.get('border_radius', 4)}px;
            padding: {dims.get('padding', 6)}px;
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: palette(highlight);
            border-width: 2px;
        }}

        /* ボタン */
        QPushButton {{
            background-color: palette(button);
            color: palette(button-text);
            border: 1px solid palette(mid);
            border-radius: {dims.get('border_radius', 4)}px;
            padding: {dims.get('padding', 6)}px {dims.get('padding_large', 12)}px;
            min-height: {dims.get('min_button_height', 24)}px;
        }}

        QPushButton:hover {{
            background-color: palette(light);
            border-color: palette(highlight);
        }}

        QPushButton:pressed {{
            background-color: palette(mid);
        }}

        QPushButton:disabled {{
            color: palette(disabled-text);
            background-color: palette(window);
        }}

        /* メニューとメニューバー */
        QMenuBar {{
            background-color: palette(window);
            color: palette(window-text);
        }}

        QMenuBar::item:selected {{
            background-color: palette(highlight);
            color: palette(highlighted-text);
        }}

        QMenu {{
            background-color: palette(base);
            color: palette(text);
            border: 1px solid palette(mid);
        }}

        QMenu::item:selected {{
            background-color: palette(highlight);
            color: palette(highlighted-text);
        }}

        /* テーブルとリスト */
        QTableView, QListView, QTreeView {{
            background-color: palette(base);
            alternate-background-color: palette(alternate-base);
            color: palette(text);
            gridline-color: palette(mid);
            selection-background-color: palette(highlight);
            selection-color: palette(highlighted-text);
        }}

        QHeaderView::section {{
            background-color: palette(window);
            color: palette(window-text);
            border: 1px solid palette(mid);
            padding: 4px;
        }}

        /* スクロールバー */
        QScrollBar:vertical {{
            background: palette(window);
            width: 12px;
            border-radius: 6px;
        }}

        QScrollBar::handle:vertical {{
            background: palette(mid);
            border-radius: 6px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: palette(light);
        }}
        """

        # カスタムスタイル追加
        if 'custom_qss' in theme:
            qss += "\n" + theme['custom_qss']

        return qss

    def _repolish_widgets(self):
        """すべてのウィジェットのスタイルを再適用"""
        for widget in self.app.allWidgets():
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def _restore_last_theme(self):
        """前回のテーマを復元"""
        last_theme = self.settings.value("theme", "dark")
        if last_theme in self.themes:
            self.apply_theme(last_theme)
        else:
            self.apply_theme("dark")
```

### デザイントークンシステム

デザイントークンは、デザインシステムの基本単位となる変数である。色、サイズ、間隔、フォントなどの視覚的属性を一元管理し、一貫性を保証する。

```json
{
  "name": "dark_professional",
  "version": "1.0.0",
  "colors": {
    "primary": {
      "main": "#2f6fff",
      "light": "#5a8fff",
      "dark": "#1a4fcc",
      "contrast": "#ffffff"
    },
    "secondary": {
      "main": "#ff6b6b",
      "light": "#ff9999",
      "dark": "#cc5555",
      "contrast": "#ffffff"
    },
    "semantic": {
      "error": "#ff5252",
      "warning": "#ffb74d",
      "success": "#4caf50",
      "info": "#2196f3"
    },
    "base": {
      "window": "#232428",
      "window_text": "#eeeeee",
      "base": "#2b2d31",
      "alternate_base": "#33353a",
      "text": "#eeeeee",
      "disabled": "#808080"
    }
  },
  "typography": {
    "font_family": {
      "primary": "Segoe UI",
      "monospace": "Consolas",
      "japanese": "Yu Gothic UI"
    },
    "font_size": {
      "xs": 8,
      "sm": 9,
      "base": 10,
      "lg": 12,
      "xl": 14,
      "xxl": 18
    },
    "font_weight": {
      "light": 300,
      "regular": 400,
      "medium": 500,
      "bold": 700
    },
    "line_height": {
      "tight": 1.2,
      "normal": 1.5,
      "relaxed": 1.8
    }
  },
  "spacing": {
    "unit": 4,
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "xxl": 32
  },
  "borders": {
    "radius": {
      "none": 0,
      "sm": 2,
      "base": 4,
      "lg": 8,
      "full": 9999
    },
    "width": {
      "thin": 1,
      "base": 2,
      "thick": 3
    }
  },
  "shadows": {
    "sm": "0 1px 2px rgba(0, 0, 0, 0.1)",
    "base": "0 2px 4px rgba(0, 0, 0, 0.15)",
    "lg": "0 4px 8px rgba(0, 0, 0, 0.2)",
    "xl": "0 8px 16px rgba(0, 0, 0, 0.25)"
  },
  "animations": {
    "duration": {
      "instant": 0,
      "fast": 150,
      "normal": 250,
      "slow": 400
    },
    "easing": {
      "linear": "linear",
      "ease": "ease",
      "ease_in": "ease-in",
      "ease_out": "ease-out",
      "ease_in_out": "ease-in-out"
    }
  },
  "breakpoints": {
    "sm": 640,
    "md": 768,
    "lg": 1024,
    "xl": 1280,
    "xxl": 1536
  }
}
```

## コンポーネント設計パターン

### ThemedWidget基底クラス

すべてのカスタムウィジェットが継承すべき基底クラスを定義する。これにより、テーマ対応が自動化される。

```python
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtCore import Signal

class ThemedWidget(QWidget):
    """テーマ対応カスタムウィジェット基底クラス"""

    theme_updated = Signal()  # テーマ更新シグナル

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_theme_connection()
        self._setup_ui()
        self._apply_theme_styles()

    def _setup_theme_connection(self):
        """ThemeManagerとの接続を確立"""
        self.theme_manager = self._get_theme_manager()
        if self.theme_manager:
            self.theme_manager.theme_changed.connect(self._on_theme_changed)

    def _get_theme_manager(self) -> Optional[ThemeManager]:
        """アプリケーションのThemeManagerインスタンスを取得"""
        app = QApplication.instance()
        if hasattr(app, 'theme_manager'):
            return app.theme_manager

        # ThemeManagerが存在しない場合は作成
        theme_manager = ThemeManager(app)
        app.theme_manager = theme_manager
        return theme_manager

    def _on_theme_changed(self, theme_name: str):
        """テーマ変更時の処理"""
        self._apply_theme_styles()
        self.theme_updated.emit()
        self.update()  # 再描画をトリガー

    def _setup_ui(self):
        """UIのセットアップ（サブクラスでオーバーライド）"""
        pass

    def _apply_theme_styles(self):
        """テーマスタイルの適用（サブクラスでオーバーライド）"""
        pass

    def get_theme_color(self, role: str) -> QColor:
        """テーマカラーを取得"""
        palette = self.palette()
        role_map = {
            'window': QPalette.Window,
            'window_text': QPalette.WindowText,
            'base': QPalette.Base,
            'text': QPalette.Text,
            'button': QPalette.Button,
            'button_text': QPalette.ButtonText,
            'highlight': QPalette.Highlight,
            'highlighted_text': QPalette.HighlightedText,
            'mid': QPalette.Mid,
            'shadow': QPalette.Shadow,
            'light': QPalette.Light
        }
        return palette.color(role_map.get(role, QPalette.Window))

    def paintEvent(self, event):
        """基本的な描画処理"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景を描画
        painter.fillRect(self.rect(), self.palette().color(QPalette.Window))

        # カスタム描画（サブクラスでオーバーライド）
        self._custom_paint(painter)

    def _custom_paint(self, painter: QPainter):
        """カスタム描画処理（サブクラスでオーバーライド）"""
        pass
```

### WidgetFactory

ファクトリーパターンを使用して、統一されたスタイルでウィジェットを生成する。

```python
from PySide6.QtWidgets import (
    QPushButton, QLineEdit, QLabel, QComboBox,
    QCheckBox, QRadioButton, QGroupBox, QFrame,
    QVBoxLayout, QHBoxLayout
)
from PySide6.QtCore import Qt
from typing import Optional, List

class WidgetFactory:
    """統一されたスタイルでウィジェットを生成するファクトリー"""

    @staticmethod
    def create_button(
        text: str,
        button_type: str = "default",
        icon_path: Optional[str] = None,
        parent: Optional[QWidget] = None
    ) -> QPushButton:
        """スタイル付きボタンを作成"""
        button = QPushButton(text, parent)

        # タイプ別スタイルクラス適用
        style_classes = {
            "default": "btn-default",
            "primary": "btn-primary",
            "secondary": "btn-secondary",
            "success": "btn-success",
            "danger": "btn-danger",
            "warning": "btn-warning",
            "info": "btn-info",
            "ghost": "btn-ghost"
        }

        if button_type in style_classes:
            button.setProperty("class", style_classes[button_type])

        # アイコン設定
        if icon_path:
            from PySide6.QtGui import QIcon
            button.setIcon(QIcon(icon_path))

        # 追加のスタイル設定
        button.setCursor(Qt.PointingHandCursor)

        return button

    @staticmethod
    def create_input_field(
        placeholder: str = "",
        input_type: str = "text",
        validator: Optional[object] = None,
        parent: Optional[QWidget] = None
    ) -> QLineEdit:
        """スタイル付き入力フィールドを作成"""
        field = QLineEdit(parent)
        field.setPlaceholderText(placeholder)

        # バリデーター設定
        if validator:
            field.setValidator(validator)

        # タイプ別設定
        if input_type == "password":
            field.setEchoMode(QLineEdit.Password)
        elif input_type == "email":
            from PySide6.QtGui import QRegularExpressionValidator
            from PySide6.QtCore import QRegularExpression
            email_regex = QRegularExpression(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            )
            field.setValidator(QRegularExpressionValidator(email_regex))

        # 統一されたスタイル適用
        field.setProperty("class", "input-field")

        return field

    @staticmethod
    def create_label(
        text: str,
        label_type: str = "default",
        parent: Optional[QWidget] = None
    ) -> QLabel:
        """スタイル付きラベルを作成"""
        label = QLabel(text, parent)

        # タイプ別スタイル
        style_map = {
            "default": "",
            "heading1": "font-size: 18px; font-weight: bold;",
            "heading2": "font-size: 14px; font-weight: bold;",
            "heading3": "font-size: 12px; font-weight: bold;",
            "caption": "font-size: 9px; color: palette(mid);",
            "error": "color: #ff5252;",
            "success": "color: #4caf50;",
            "warning": "color: #ffb74d;"
        }

        if label_type in style_map and style_map[label_type]:
            label.setStyleSheet(style_map[label_type])

        return label

    @staticmethod
    def create_card_widget(
        title: str,
        content: Optional[QWidget] = None,
        actions: Optional[List[QPushButton]] = None,
        parent: Optional[QWidget] = None
    ) -> QFrame:
        """カード型コンテナウィジェット"""
        card = QFrame(parent)
        card.setProperty("class", "card-widget")
        card.setFrameStyle(QFrame.Box)

        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # タイトル
        if title:
            title_label = WidgetFactory.create_label(title, "heading2")
            title_label.setProperty("class", "card-title")
            layout.addWidget(title_label)

            # セパレータ
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setProperty("class", "card-separator")
            layout.addWidget(separator)

        # コンテンツ
        if content:
            layout.addWidget(content)

        # アクションボタン
        if actions:
            action_layout = QHBoxLayout()
            action_layout.addStretch()
            for button in actions:
                action_layout.addWidget(button)
            layout.addLayout(action_layout)

        # カードスタイル
        card.setStyleSheet("""
            QFrame[class="card-widget"] {
                background-color: palette(base);
                border: 1px solid palette(mid);
                border-radius: 8px;
            }
        """)

        return card

    @staticmethod
    def create_form_group(
        label_text: str,
        widget: QWidget,
        help_text: str = "",
        required: bool = False,
        parent: Optional[QWidget] = None
    ) -> QWidget:
        """フォームグループ（ラベル付きウィジェット）を作成"""
        container = QWidget(parent)
        layout = QVBoxLayout(container)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        # ラベル
        label_str = label_text
        if required:
            label_str += " *"
        label = WidgetFactory.create_label(label_str)
        label.setProperty("class", "form-label")
        layout.addWidget(label)

        # ウィジェット
        layout.addWidget(widget)

        # ヘルプテキスト
        if help_text:
            help_label = WidgetFactory.create_label(help_text, "caption")
            help_label.setProperty("class", "form-help")
            layout.addWidget(help_label)

        return container
```

### 複合ウィジェットの実装例

実際のアプリケーションで使用される複合ウィジェットの実装例を示す。

```python
from PySide6.QtWidgets import QHBoxLayout, QCompleter
from PySide6.QtCore import Signal, QTimer, Qt
from PySide6.QtGui import QIcon, QPixmap
from pathlib import Path

class SearchBar(ThemedWidget):
    """テーマ対応検索バーコンポーネント"""

    search_triggered = Signal(str)  # 検索実行シグナル
    text_changed = Signal(str)      # テキスト変更シグナル

    def __init__(self, parent=None, placeholder="検索...",
                 show_icon=True, enable_suggestions=True):
        self.placeholder = placeholder
        self.show_icon = show_icon
        self.enable_suggestions = enable_suggestions
        self.search_timer = QTimer()
        self.search_timer.setInterval(300)  # 300ms debounce
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._on_search_timeout)

        super().__init__(parent)

    def _setup_ui(self):
        """UIのセットアップ"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # 検索アイコン
        if self.show_icon:
            self.icon_label = QLabel()
            self.icon_label.setProperty("class", "search-icon")
            self.icon_label.setFixedSize(16, 16)
            layout.addWidget(self.icon_label)

        # 入力フィールド
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.placeholder)
        self.search_input.setProperty("class", "search-input")
        self.search_input.returnPressed.connect(self._on_search)
        self.search_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.search_input)

        # クリアボタン
        self.clear_button = QPushButton("✕")
        self.clear_button.setProperty("class", "clear-button")
        self.clear_button.setFixedSize(20, 20)
        self.clear_button.clicked.connect(self.clear_search)
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.setVisible(False)
        layout.addWidget(self.clear_button)

        # 検索ボタン（オプション）
        self.search_button = QPushButton("検索")
        self.search_button.setProperty("class", "search-button")
        self.search_button.clicked.connect(self._on_search)
        self.search_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.search_button)

        # 自動補完設定
        if self.enable_suggestions:
            self._setup_completer()

    def _setup_completer(self):
        """自動補完の設定"""
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.search_input.setCompleter(self.completer)

    def set_suggestions(self, suggestions: List[str]):
        """検索候補を設定"""
        if self.enable_suggestions and hasattr(self, 'completer'):
            self.completer.setModel(QStringListModel(suggestions))

    def _apply_theme_styles(self):
        """テーマスタイルの適用"""
        # アイコンの更新
        if self.show_icon and hasattr(self, 'icon_label'):
            self._update_search_icon()

        # ウィジェット全体のスタイル
        self.setStyleSheet("""
            SearchBar {
                background-color: palette(base);
                border: 1px solid palette(mid);
                border-radius: 20px;
            }

            QLineEdit[class="search-input"] {
                border: none;
                background-color: transparent;
                padding: 4px;
            }

            QPushButton[class="clear-button"] {
                border: none;
                background-color: transparent;
                color: palette(mid);
                font-weight: bold;
            }

            QPushButton[class="clear-button"]:hover {
                color: palette(highlight);
            }

            QPushButton[class="search-button"] {
                border: none;
                background-color: palette(highlight);
                color: palette(highlighted-text);
                padding: 4px 12px;
                border-radius: 12px;
            }

            QPushButton[class="search-button"]:hover {
                background-color: palette(light);
            }
        """)

    def _update_search_icon(self):
        """テーマに応じた検索アイコンの更新"""
        if not self.theme_manager:
            return

        # テーマに応じたアイコンパス
        theme_name = self.theme_manager.current_theme or "dark"
        icon_path = Path(f"icons/{theme_name}/search.svg")

        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            self.icon_label.setPixmap(pixmap.scaled(16, 16, Qt.KeepAspectRatio,
                                                   Qt.SmoothTransformation))
        else:
            # フォールバック：テキストアイコン
            self.icon_label.setText("🔍")

    def _on_text_changed(self, text: str):
        """テキスト変更時の処理"""
        self.clear_button.setVisible(bool(text))
        self.text_changed.emit(text)

        # Debounce検索
        self.search_timer.stop()
        if text:
            self.search_timer.start()

    def _on_search_timeout(self):
        """Debounce後の検索実行"""
        text = self.search_input.text()
        if text:
            self.search_triggered.emit(text)

    def _on_search(self):
        """検索実行"""
        text = self.search_input.text()
        if text:
            self.search_triggered.emit(text)

    def clear_search(self):
        """検索をクリア"""
        self.search_input.clear()
        self.clear_button.setVisible(False)

    def set_focus(self):
        """フォーカスを設定"""
        self.search_input.setFocus()

    def get_text(self) -> str:
        """現在のテキストを取得"""
        return self.search_input.text()

    def set_text(self, text: str):
        """テキストを設定"""
        self.search_input.setText(text)
```

## 統一性維持のガイドライン

### コーディング規約

テーマシステムの一貫性を保つため、以下の規約を厳守する。

#### 必須ルール

1. **palette()参照の使用**
   ```python
   # ✅ 良い例
   widget.setStyleSheet("background-color: palette(window);")

   # ❌ 悪い例
   widget.setStyleSheet("background-color: #232428;")
   ```

2. **Fusionスタイルの適用**
   ```python
   # アプリケーション初期化時に必須
   app.setStyle("Fusion")
   ```

3. **ThemedWidget基底クラスの継承**
   ```python
   class MyCustomWidget(ThemedWidget):
       def _setup_ui(self):
           # UI構築
           pass

       def _apply_theme_styles(self):
           # テーマスタイル適用
           pass
   ```

### 機能追加時のチェックリスト

新機能を追加する際は、以下のチェックリストを使用して統一性を確保する。

```markdown
## 新機能実装チェックリスト

### 設計フェーズ
- [ ] 既存のデザイントークンで実装可能か確認
- [ ] 新しい色が必要な場合、セマンティックカラーから選択
- [ ] カスタムウィジェットはThemedWidget基底クラスを継承
- [ ] WidgetFactoryの利用を検討

### 実装フェーズ
- [ ] palette()参照のみを使用（直接色指定禁止）
- [ ] Fusionスタイルでの動作確認
- [ ] プロパティによるスタイルクラス設定
- [ ] テーマ変更シグナルへの対応

### テストフェーズ
- [ ] ライトテーマでの表示確認
- [ ] ダークテーマでの表示確認
- [ ] テーマ切り替え時の再描画確認
- [ ] 無効状態での表示確認
- [ ] HiDPI環境での表示確認

### ドキュメント
- [ ] コンポーネントカタログへの追加
- [ ] スタイルガイドの更新
- [ ] 使用例の作成
```

### 命名規則とスタイルクラス

BEM（Block Element Modifier）風の命名規則を採用する。

```python
# ブロック（独立したコンポーネント）
"search-bar"
"user-card"
"navigation-menu"

# エレメント（ブロックの構成要素）
"search-bar__input"
"search-bar__button"
"user-card__avatar"
"user-card__name"

# モディファイア（状態やバリエーション）
"search-bar--compact"
"search-bar__button--disabled"
"user-card--selected"

# プロパティ設定例
widget.setProperty("class", "search-bar")
input_field.setProperty("class", "search-bar__input")
button.setProperty("state", "disabled")
```

## パフォーマンスとアクセシビリティ

### 遅延読み込みとキャッシュ

大規模なアプリケーションでは、スタイルの遅延読み込みとキャッシュが重要となる。

```python
from functools import lru_cache
from typing import Dict
import time

class StyleCache:
    """スタイルシートのキャッシュ管理"""

    def __init__(self, max_size: int = 128):
        self._cache: Dict[str, tuple[str, float]] = {}
        self._max_size = max_size
        self._access_count: Dict[str, int] = {}

    @lru_cache(maxsize=128)
    def load_style(self, style_path: str) -> str:
        """スタイルシートを読み込み（キャッシュ付き）"""
        path = Path(style_path)
        if not path.exists():
            return ""

        # ファイルの更新時刻をチェック
        mtime = path.stat().st_mtime

        if style_path in self._cache:
            cached_content, cached_mtime = self._cache[style_path]
            if cached_mtime == mtime:
                self._access_count[style_path] = self._access_count.get(style_path, 0) + 1
                return cached_content

        # ファイルを読み込み
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # キャッシュに保存
        self._cache[style_path] = (content, mtime)
        self._access_count[style_path] = 1

        # キャッシュサイズ制限
        if len(self._cache) > self._max_size:
            self._evict_least_used()

        return content

    def _evict_least_used(self):
        """最も使用頻度の低いエントリを削除"""
        if not self._access_count:
            return

        least_used = min(self._access_count, key=self._access_count.get)
        del self._cache[least_used]
        del self._access_count[least_used]

    def clear(self):
        """キャッシュをクリア"""
        self._cache.clear()
        self._access_count.clear()
        self.load_style.cache_clear()
```

### WCAG準拠のコントラスト比

アクセシビリティのため、WCAG 2.1のコントラスト比基準を満たす必要がある。

```python
from PySide6.QtGui import QColor
import math

def calculate_contrast_ratio(color1: QColor, color2: QColor) -> float:
    """WCAG 2.1準拠のコントラスト比計算"""
    def relative_luminance(color: QColor) -> float:
        """相対輝度を計算"""
        def adjust(val):
            val = val / 255.0
            return val / 12.92 if val <= 0.03928 else ((val + 0.055) / 1.055) ** 2.4

        r, g, b = adjust(color.red()), adjust(color.green()), adjust(color.blue())
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    l1 = relative_luminance(color1)
    l2 = relative_luminance(color2)

    lighter = max(l1, l2)
    darker = min(l1, l2)

    return (lighter + 0.05) / (darker + 0.05)

def check_accessibility(widget: QWidget) -> Dict[str, any]:
    """ウィジェットのアクセシビリティをチェック"""
    results = {
        'contrast_ratio': None,
        'passes_aa': False,
        'passes_aaa': False,
        'recommendations': []
    }

    palette = widget.palette()
    bg_color = palette.color(QPalette.Window)
    fg_color = palette.color(QPalette.WindowText)

    ratio = calculate_contrast_ratio(bg_color, fg_color)
    results['contrast_ratio'] = ratio

    # WCAG基準
    # AA: 通常テキスト 4.5:1、大きいテキスト 3:1
    # AAA: 通常テキスト 7:1、大きいテキスト 4.5:1
    results['passes_aa'] = ratio >= 4.5
    results['passes_aaa'] = ratio >= 7.0

    if not results['passes_aa']:
        results['recommendations'].append(
            f"コントラスト比が不足しています（{ratio:.2f}:1）。"
            "最低4.5:1が必要です。"
        )

    return results
```

## テストとバリデーション

### pytest-qtによる自動テスト

テーマシステムの品質を保証するため、包括的なテストスイートを実装する。

```python
import pytest
from pytest_qt.qtbot import QtBot
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtGui import QPalette

class TestThemeSystem:
    """テーマシステムのテストスイート"""

    @pytest.fixture
    def app(self, qtbot):
        """テスト用アプリケーション"""
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        return app

    @pytest.fixture
    def theme_manager(self, app, qtbot):
        """テスト用ThemeManager"""
        manager = ThemeManager(app)
        app.theme_manager = manager
        return manager

    def test_theme_initialization(self, theme_manager):
        """テーマ初期化のテスト"""
        assert theme_manager is not None
        assert 'dark' in theme_manager.themes
        assert 'light' in theme_manager.themes

    def test_theme_switching(self, theme_manager, qtbot):
        """テーマ切り替えのテスト"""
        # ダークテーマ適用
        with qtbot.waitSignal(theme_manager.theme_changed, timeout=1000):
            theme_manager.apply_theme("dark")

        assert theme_manager.current_theme == "dark"

        # パレット確認
        palette = QApplication.instance().palette()
        window_color = palette.color(QPalette.Window)
        assert window_color.name() == "#232428"

        # ライトテーマ切り替え
        with qtbot.waitSignal(theme_manager.theme_changed, timeout=1000):
            theme_manager.apply_theme("light")

        assert theme_manager.current_theme == "light"
        window_color = palette.color(QPalette.Window)
        assert window_color.name() == "#f4f5f6"

    def test_widget_theme_inheritance(self, theme_manager, qtbot):
        """ウィジェットのテーマ継承テスト"""
        widget = ThemedWidget()
        qtbot.addWidget(widget)

        # テーマ変更
        theme_manager.apply_theme("dark")

        # ウィジェットのパレット確認
        widget_palette = widget.palette()
        app_palette = QApplication.instance().palette()

        assert widget_palette.color(QPalette.Window) == app_palette.color(QPalette.Window)

    def test_contrast_ratio(self, theme_manager):
        """コントラスト比のテスト"""
        for theme_name in ["dark", "light"]:
            theme_manager.apply_theme(theme_name)
            palette = QApplication.instance().palette()

            ratio = calculate_contrast_ratio(
                palette.color(QPalette.Window),
                palette.color(QPalette.WindowText)
            )

            # WCAG AA基準（4.5:1以上）
            assert ratio >= 4.5, f"{theme_name}テーマのコントラスト比が不足: {ratio:.2f}"

    def test_widget_factory(self, theme_manager, qtbot):
        """WidgetFactoryのテスト"""
        # ボタン作成
        button = WidgetFactory.create_button("Test", "primary")
        qtbot.addWidget(button)

        assert button.text() == "Test"
        assert button.property("class") == "btn-primary"

        # 入力フィールド作成
        field = WidgetFactory.create_input_field("Enter text", "email")
        qtbot.addWidget(field)

        assert field.placeholderText() == "Enter text"
        assert field.property("class") == "input-field"

    def test_search_bar_functionality(self, theme_manager, qtbot):
        """SearchBarコンポーネントのテスト"""
        search_bar = SearchBar()
        qtbot.addWidget(search_bar)

        # テキスト入力
        search_bar.set_text("test query")
        assert search_bar.get_text() == "test query"

        # 検索シグナル
        with qtbot.waitSignal(search_bar.search_triggered, timeout=1000) as blocker:
            search_bar.search_input.returnPressed.emit()

        assert blocker.args[0] == "test query"

        # クリア機能
        search_bar.clear_search()
        assert search_bar.get_text() == ""

    @pytest.mark.parametrize("theme", ["dark", "light"])
    def test_theme_persistence(self, theme_manager, theme):
        """テーマ設定の永続化テスト"""
        theme_manager.apply_theme(theme)

        # 設定が保存されていることを確認
        settings = theme_manager.settings
        saved_theme = settings.value("theme")
        assert saved_theme == theme

    def test_style_cache_performance(self, qtbot):
        """スタイルキャッシュのパフォーマンステスト"""
        cache = StyleCache()

        # テストファイル作成
        test_file = Path("test_style.qss")
        test_file.write_text("QWidget { color: palette(window-text); }")

        try:
            # 初回読み込み
            import time
            start = time.perf_counter()
            content1 = cache.load_style(str(test_file))
            first_load_time = time.perf_counter() - start

            # キャッシュからの読み込み
            start = time.perf_counter()
            content2 = cache.load_style(str(test_file))
            cached_load_time = time.perf_counter() - start

            assert content1 == content2
            assert cached_load_time < first_load_time
        finally:
            test_file.unlink()
```

## 既存プロジェクトの移行

### 移行分析ツール

既存のコードベースを分析し、テーマシステムへの移行に必要な変更を特定する。

```python
import ast
import re
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

class ThemeMigrationAnalyzer:
    """既存コードのテーマ移行分析ツール"""

    def __init__(self):
        self.issues: List[Dict] = []
        self.statistics = {
            'total_files': 0,
            'files_with_issues': 0,
            'direct_colors': 0,
            'hardcoded_styles': 0,
            'missing_fusion': 0
        }

    def analyze_project(self, project_path: Path) -> Dict:
        """プロジェクト全体を分析"""
        results = {
            'summary': {},
            'files': [],
            'recommendations': []
        }

        py_files = list(project_path.rglob("*.py"))
        self.statistics['total_files'] = len(py_files)

        for py_file in py_files:
            file_issues = self.analyze_file(py_file)
            if file_issues['issues']:
                self.statistics['files_with_issues'] += 1
                results['files'].append(file_issues)

        results['summary'] = self.statistics
        results['recommendations'] = self._generate_recommendations()

        return results

    def analyze_file(self, file_path: Path) -> Dict:
        """単一ファイルを分析"""
        analysis = {
            'file': str(file_path),
            'issues': [],
            'line_numbers': [],
            'severity': 'low'
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            analysis['issues'].append(f"ファイル読み込みエラー: {e}")
            return analysis

        # 直接色指定の検出
        color_pattern = re.compile(r'#[0-9a-fA-F]{6}|rgb\([^)]+\)|rgba\([^)]+\)')
        style_pattern = re.compile(r'setStyleSheet\([^)]+\)')

        for i, line in enumerate(lines, 1):
            # 直接色指定
            if color_pattern.search(line):
                if 'setStyleSheet' in line or 'QColor' in line:
                    analysis['issues'].append({
                        'type': 'direct_color',
                        'line': i,
                        'content': line.strip(),
                        'severity': 'high'
                    })
                    self.statistics['direct_colors'] += 1

            # ハードコードされたスタイル
            if style_pattern.search(line) and 'palette(' not in line:
                analysis['issues'].append({
                    'type': 'hardcoded_style',
                    'line': i,
                    'content': line.strip(),
                    'severity': 'medium'
                })
                self.statistics['hardcoded_styles'] += 1

        # Fusionスタイルの使用確認
        if 'QApplication' in content and 'setStyle' not in content:
            analysis['issues'].append({
                'type': 'missing_fusion',
                'severity': 'medium',
                'description': 'Fusionスタイルが設定されていません'
            })
            self.statistics['missing_fusion'] += 1

        # 重要度の判定
        if any(issue.get('severity') == 'high' for issue in analysis['issues']):
            analysis['severity'] = 'high'
        elif any(issue.get('severity') == 'medium' for issue in analysis['issues']):
            analysis['severity'] = 'medium'

        return analysis

    def _generate_recommendations(self) -> List[str]:
        """推奨事項を生成"""
        recommendations = []

        if self.statistics['direct_colors'] > 0:
            recommendations.append(
                f"直接色指定が{self.statistics['direct_colors']}箇所見つかりました。"
                "palette()参照に置き換えてください。"
            )

        if self.statistics['hardcoded_styles'] > 0:
            recommendations.append(
                f"ハードコードされたスタイルが{self.statistics['hardcoded_styles']}箇所あります。"
                "ThemedWidgetまたはWidgetFactoryの使用を検討してください。"
            )

        if self.statistics['missing_fusion'] > 0:
            recommendations.append(
                "Fusionスタイルが設定されていないファイルがあります。"
                "app.setStyle('Fusion')を追加してください。"
            )

        return recommendations

    def generate_report(self, results: Dict, output_path: Path):
        """移行レポートを生成"""
        report = ["# テーマ移行分析レポート\n"]
        report.append(f"生成日時: {datetime.now().isoformat()}\n")

        # サマリー
        report.append("## サマリー\n")
        summary = results['summary']
        report.append(f"- 総ファイル数: {summary['total_files']}")
        report.append(f"- 問題のあるファイル: {summary['files_with_issues']}")
        report.append(f"- 直接色指定: {summary['direct_colors']}箇所")
        report.append(f"- ハードコードスタイル: {summary['hardcoded_styles']}箇所\n")

        # ファイル別の詳細
        report.append("## ファイル別詳細\n")
        for file_info in results['files']:
            report.append(f"\n### {file_info['file']}")
            report.append(f"重要度: {file_info['severity']}")

            for issue in file_info['issues']:
                if 'line' in issue:
                    report.append(f"- L{issue['line']}: {issue['type']}")
                    report.append(f"  ```python\n  {issue['content']}\n  ```")
                else:
                    report.append(f"- {issue['type']}: {issue.get('description', '')}")

        # 推奨事項
        report.append("\n## 推奨事項\n")
        for rec in results['recommendations']:
            report.append(f"- {rec}")

        # 移行手順
        report.append("\n## 移行手順\n")
        report.append(self._get_migration_steps())

        # レポート保存
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))

    def _get_migration_steps(self) -> str:
        """移行手順を取得"""
        return """
### フェーズ1: 準備（1週間）
1. ThemeManagerクラスの実装
2. デフォルトテーマ（dark/light）の定義
3. テストスイートの準備

### フェーズ2: コア実装（2週間）
1. QApplicationへのThemeManager統合
2. app.setStyle("Fusion")の追加
3. グローバルQSSの適用

### フェーズ3: コンポーネント移行（3週間）
1. 直接色指定をpalette()参照に置換
2. カスタムウィジェットをThemedWidget継承に変更
3. WidgetFactoryの導入

### フェーズ4: テストと最適化（1週間）
1. 全テーマでの動作確認
2. コントラスト比の検証
3. パフォーマンステスト
4. ドキュメント作成
"""
```

## まとめ

本記事では、PySide6アプリケーションにおける包括的なテーマ設計システムを詳細に解説した。QPaletteベースの設計、ThemeManagerによる一元管理、デザイントークンシステムの組み合わせにより、以下の成果を実現できる。

**実装のキーポイント：**
1. **QPaletteとpalette()参照**：動的なテーマ切り替えの基盤
2. **Fusionスタイル**：クロスプラットフォーム対応の必須要素
3. **ThemeManager**：シングルトンパターンによる一元管理
4. **ThemedWidget基底クラス**：自動的なテーマ対応
5. **WidgetFactory**：統一されたコンポーネント生成

**次のステップ：**
- 既存プロジェクトへの段階的移行
- カスタムテーマの作成と配布
- アクセシビリティ機能の強化
- パフォーマンスモニタリングの実装

このテーマシステムを導入することで、保守性が高く、ユーザー体験に優れたPySide6アプリケーションを構築できる。機能追加時も一貫性を保ちながら、効率的な開発が可能となる。

## 参考リソース

- [Qt for Python公式ドキュメント](https://doc.qt.io/qtforpython-6/)
- [PySide6 APIリファレンス](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/index.html)
- [WCAG 2.1ガイドライン](https://www.w3.org/WAI/WCAG21/quickref/)
- [本記事のサンプルコード（GitHub）](https://github.com/example/pyside6-theme-system)