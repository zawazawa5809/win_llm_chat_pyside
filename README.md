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
4. メッセージを入力して「送信」

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

- `src/win_llm_chat_pyside/app.py`: エントリポイント
- `src/win_llm_chat_pyside/ui_main.py`: GUI（MainWindow, SettingsDialog）
- `src/win_llm_chat_pyside/client.py`: LLM クライアント（OpenAI 互換 / Ollama）
- `src/win_llm_chat_pyside/config.py`: 設定管理
- `src/win_llm_chat_pyside/models.py`: ドメインモデル（Message）
- `src/win_llm_chat_pyside/storage.py`: 将来の履歴永続化用（スタブ）

## 設定ファイル

- 保存先: `%APPDATA%\win-llm-chat-pyside\config.json`

## ライセンス

MIT License

