# Design Document

## Overview

Option C（ハイブリッド）で、送信処理を Worker（スレッド or スレッドプール）へ委譲し UI フリーズを解消しつつ、キーバインド（Enter 改行/Ctrl+Enter 送信）、応答待ちインジケータ、自動スクロール、Markdown 表示の微調整を段階導入する。

## Architecture

```text
[MainWindow]
  ├── ChatView (QTextBrowser)
  ├── Input (QPlainTextEdit)
  ├── SendButton
  ├── BusyIndicator (inline or overlay)
  └── ChatWorker (QRunnable/QThread)
        ↓ emits (finished(result:str), failed(error:LlmClientError), elapsed_ms:int)
     [OpenAiCompatibleClient|OllamaClient]
```

### Components

- ChatWorker（新規）
  - 役割: `messages: list[Message]` を受け取り、`client.send_chat(messages)` をバックグラウンドで実行
  - シグナル:
    - `succeeded(content: str, elapsed_ms: int)`
    - `failed(user_message: str, detail: str, elapsed_ms: int)`
  - 例外分類は `client.py` の例外を受けて UI 文言へ変換（詳細は「Error Map」）
- UI 拡張
  - 応答待ち中のインジケータ表示/非表示
  - 自動スクロール（送信直後・応答反映直後）
  - キーバインド: Enter 改行 / Ctrl+Enter 送信（設定で切替可）
- Markdown Style
  - `QTextBrowser.setStyleSheet()` による基本のタイポグラフィ調整
  - コードブロック/インラインコードの背景・等幅・横スクロール
  - HTML はデフォルトでサニタイズ（任意で無効化）

## Threading Model

- 実装案 A: `QThread` + QObject Worker
  - Worker にスロット `run()` を持たせ、`QThread` へ `moveToThread()`
  - Pros: 分かりやすいライフサイクル、Qt シグナル/スロットで完結
  - Cons: ボイラープレート多め
- 実装案 B: `QThreadPool` + `QRunnable`
  - `QThreadPool.globalInstance().start(runnable)` で投入
  - Pros: シンプル、複数同時ジョブにも対応しやすい
  - Cons: シグナルを直接使いにくく、ラッパが必要
- 採用: A（`QThread`）を推奨。まず一度に 1 ジョブのみ許容（送信中ロックと整合）

## UI State Transitions

1. Idle → Sending
   - send_button.disable / input.disable
   - show_wait_indicator
   - start_worker(messages, config_timeouts)
2. Sending → Succeeded(content)
   - append assistant message
   - update chat view
   - autoscroll_to_end
   - hide_wait_indicator
   - input.clear / input.enable / send_button.enable
3. Sending → Failed(user_message, detail)
   - show_error_dialog(user_message)
   - log(detail)
   - hide_wait_indicator
   - input.enable / send_button.enable

## Keybindings

- 既定: Enter 改行 / Ctrl+Enter 送信
- 実装: `QPlainTextEdit` に eventFilter で `QKeyEvent`
  - Ctrl+Enter 検出で送信トリガ
  - Enter 単体は改行、Shift+Enter も改行
- 設定で `ui.enter_to_send` が true の場合は逆挙動へ切替

## Auto Scroll

- ビュー更新後に末尾へ移動
  - `cursor = self.chat_view.textCursor(); cursor.movePosition(QTextCursor.End); self.chat_view.setTextCursor(cursor); self.chat_view.ensureCursorVisible()`
- 将来、ユーザーが上方向にスクロール中は抑制（本仕様では常時スクロール）

## Markdown Style

- StyleSheet（例）
  - 本文: `font-family: system-ui, "Segoe UI"; font-size: 11pt; line-height: 1.6;`
  - 見出し: マージン調整、過度なサイズ差を抑制
  - コードブロック: 等幅フォント、背景、パディング、横スクロール
  - 行内コード: 背景薄色、角丸
  - 表: 横スクロール許容
- HTML サニタイズ: 受信テキスト前処理で簡易フィルタ（タグの除去/エスケープ）を適用可能に

## Config Schema

- 追加キー（requirements に準拠）
  - `ui.enter_to_send: bool`（既定: false）
  - `ui.ctrl_enter_to_send: bool`（既定: true）
  - `ui.autoscroll_enabled: bool`（既定: true）
  - `ui.wait_indicator_style: str`（例: "spinner"）
  - `ui.markdown.font_family: str`（例: "system-ui"）
  - `ui.markdown.font_size_pt: int`（例: 11）
  - `ui.markdown.line_height: float`（例: 1.6）
  - `network.request_timeout_ms: int`（既定: 30000）
  - `network.connect_timeout_ms: int`（既定: 10000）
- `config.py`:
  - `Config` に上記フィールドを追加（後方互換のため既定値付き）
  - 読込/保存は既存関数を踏襲
- `SettingsDialog`:
  - 今回はネットワークタイムアウトのみ UI 追加（UI 膨張を避ける）
  - キーバインド/Markdown 見た目は将来の設定画面拡張で露出

## Error Map（UI 文言）

- 401/403: 認証に失敗しました（API キーを確認してください）
- 404: エンドポイントが見つかりません
- 408/Timeout: 応答がタイムアウトしました
- 429: リクエストが多すぎます（しばらく待ってから再試行）
- 5xx: サーバでエラーが発生しました
- 接続失敗: サーバに接続できません
- JSON/パース失敗: 不正な応答を受信しました
- それ以外: 通信中にエラーが発生しました
- ログは detail（例外/本文先頭）と所要時間を記録

## Telemetry / Logging

- 記録項目: start/end、elapsed_ms、エラー種別、HTTP ステータス（わかる範囲）
- 実装: 現状は `print()` ベースで十分。将来 `logging` へ切替可能にする。

## Test Strategy

- `client.py`: 既存ユニットテスト継続
- Worker: 例外 →UI 文言変換の単体テスト（変換関数を分離）
- UI: スモーク（送信 → 応答 → スクロール/ロック解除）

## Open Questions

- HTML サニタイズの厳格度（外部ライブラリ導入の是非）
- タイムアウトの connect/read 分離を UI に露出するか
