# win-llm-chat-pyside

Windows 10/11 向けの軽量 PySide6 製 LLM チャットクライアント。

## 概要

- **目的**: 低スペック Windows 端末でも軽快に動作する LLM チャットクライアント
- **対象**: Ollama / OpenAI 互換エンドポイント
- **配布**: PyInstaller による単一 EXE 配布

## セットアップ

### 1. 仮想環境の作成と依存のインストール

```powershell
# uv で仮想環境を作成
uv venv .venv

# 仮想環境を有効化（PowerShell）
.\.venv\Scripts\Activate.ps1

# 依存をインストール
uv sync
```

### 2. アプリケーションの実行

```powershell
python -m win_llm_chat_pyside.app
```

## 使い方

1. アプリを起動
2. 「設定」メニューから「接続設定...」を開く
3. ベース URL、モデル名、API キー（任意）を設定
4. 右ペイン上部の「チャット」タブでメッセージを入力して「送信」
5. 添付ファイルの参照や検索を行いたい場合は右ペインの「添付」タブに切り替える（`Ctrl+1` でチャット、`Ctrl+2` で添付に切り替え可能）

## ビルド（単一 EXE）

```powershell
# PyInstaller をインストール（dev 依存に含まれていない場合）
pip install pyinstaller

# ビルド
pyinstaller build.spec

# 生成された EXE
# dist/LLMChatClient.exe
```

## 構成

ソースコードは `src/win_llm_chat_pyside/` 配下に機能別に構造化されています。

- `app.py`: アプリケーションエントリポイント
- `core/`: 基盤ロジック（Config, Logger, Factory）
- `features/`: 機能ごとのモジュール（Chat, Sessions, Attachments, Search, Prompts, Roles）
- `services/`: インフラストラクチャ（LLM Client, Storage, Workers）
- `ui/`: GUI コンポーネント（MainWindow, Dialogs, Styles）
- `models/`: ドメインモデル

## 設定ファイル

- 保存先: `%APPDATA%\win-llm-chat-pyside\config.json`

### 主な設定キー

- 接続
  - `base_url`: エンドポイントのベース URL（例: `http://localhost:11434`）
  - `model`: モデル名（例: `llama3`）
  - `api_key`: 必要に応じて設定（OpenAI 互換など）
- タイムアウト
  - `connect_timeout_ms`: 通常接続タイムアウト（既定 10000）
  - `request_timeout_ms`: 通常リードタイムアウト（既定 30000）
  - `stream_connect_timeout_ms`: ストリーミング接続タイムアウト（既定 5000）
  - `stream_total_timeout_ms`: ストリーミング全体タイムアウト（既定 30000）
- UI
  - `ui_ctrl_enter_to_send`: Ctrl+Enter で送信（既定 true）
  - `ui_enter_to_send`: Enter で送信（既定 false）
  - `ui_autoscroll_enabled`: 自動スクロール（既定 true）
  - `ui_streaming_stop_enabled`: 「停止」ボタン有効（既定 true）
  - `ui_markdown_*`: フォント/サイズ/行間など
  - `ui_main_selected_tab`: 起動時に選択されるメインタブ（`"chat"` / `"attachments"`）

### 既知の制約・注意事項

- ストリーミング
  - OpenAI 互換は SSE（`data:` 行）、Ollama は JSON Lines。両方 UTF-8 前提で処理
  - サーバが文字コードを誤報告する場合は `utf-8` に強制デコードして処理
  - ネットワーク断や不正フレームは安全側でスキップし、最終的にエラー通知
- UI
  - 非対応エンドポイントは一括応答にフォールバック
  - 停止ボタンはストリーム処理に対する中断要求（即時停止を保証しない）

## ライセンス

MIT License

