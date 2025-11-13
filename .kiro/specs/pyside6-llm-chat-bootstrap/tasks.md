# Tasks

## 1. リポジトリセットアップ

- [x] Python 環境定義（`pyproject.toml`）
  - 依存: `PySide6`, `requests` or `httpx`, `typing-extensions`（必要時）
- [x] `.gitignore` 整備（`__pycache__`, `.venv`, `dist`, `build` 等）
- [x] `src/` ディレクトリ作成
- [x] 仮想環境作成（`uv venv .venv`）
- [x] 依存同期（`uv sync` により `pyproject.toml` と `uv.lock` を反映）
- [x] 仮想環境の有効化（Windows: `.\.venv\Scripts\Activate.ps1`）

Acceptance:

- `.venv` が作成され、アクティベートできる（Windows PowerShell: `.\.venv\Scripts\Activate.ps1`）
- `uv sync` が成功し依存が解決される
- `src/` が作成済み

## 2. PySide6 アプリ骨格

- [x] `src/app.py` エントリポイント
  - `QApplication` 起動、未処理例外のトップレベルハンドリング
- [x] `src/ui_main.py` の雛形（`MainWindow` / `SettingsDialog`）
  - `QTextBrowser` 表示、`QPlainTextEdit` 入力、送信ボタン配置
  - 送信中は送信ボタン disable

Acceptance:

- 起動して空のウィンドウが表示される
- ダミー送信でビュー更新される

## 3. モデルと設定

- [x] `src/models.py` に `Message` dataclass（role, content）
- [x] `src/config.py` に `Config` dataclass と `load_config` / `save_config`
  - 既定保存先: `%APPDATA%/win-llm-chat-pyside/config.json`
  - バリデーション（URL 形式、空文字チェックの最低限）

Acceptance:

- 設定ファイルが保存/読込できる
- 不正値はユーザーに知らせる

## 4. LLM クライアント

- [x] `src/client.py` に `BaseLlmClient`（Protocol/ABC）と実装
  - [x] `OpenAiCompatibleClient`: `/v1/chat/completions` 実装
  - [x] `OllamaClient`（任意）: `/api/chat` 実装
- [x] 例外整形（接続/認証/フォーマット）とタイムアウト

Acceptance:

- 正常系で content を取得可能
- 失敗系で意味あるメッセージを返す

## 5. 統合（UI ↔ LlmClient）

- [x] `MainWindow` に `LlmClient` を注入
- [x] 入力を `Message(role="user")` として内部履歴へ追加
- [x] `send_chat(messages)` 応答を `Message(role="assistant")` で追加
- [x] Markdown 生成して `QTextBrowser.setMarkdown()` 更新

Acceptance:

- 入力 → 送信 →Markdown 表示が確認できる
- 送信中は UI が抑制される

## 6. エラー表示

- [x] 代表的エラーの分類とメッセージ表示（`QMessageBox` 等）
- [x] 設定不足や URL 不正時のガード

Acceptance:

- ネットワーク/認証/フォーマットエラーがユーザーに明確に伝わる
- アプリは継続動作する

## 7. パッケージング

- [x] PyInstaller 設定（GUI モード、単一 EXE）
- [x] `build` / `dist` 出力と別マシンでの起動確認

Acceptance:

- 起動時間が目標範囲に収まる（目安 2 秒前後）
- 常駐メモリがおおむね 300MB 以下

## 8. テスト

- [x] `client.py` ユニットテスト（HTTP モック）
- [x] 簡易手動テスト項目（正常/異常）

Acceptance:

- ユニットテストが成功する
- 手動テストチェックリストを満たす

## 9. 将来拡張の下地

- [x] `storage.py` の最小 API スタブ（save/load）
- [x] 設定拡張の受け皿（プロキシ/タイムアウト項目のフィールドのみ）

Acceptance:

- API スタブ呼出で例外が発生しない
- 将来の設定項目追加が容易な構造である
