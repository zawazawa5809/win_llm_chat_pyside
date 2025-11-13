# Tasks

## Overview
設計（Option C）に基づき、送信ワーカー導入と UI/UX 改善を段階的に実装するタスク分解。

## Task List

- [x] Implement ChatWorker with QThread
   - Create `ChatWorker` (QObject) with `run(messages: list[Message], client)` 
   - Signals: `succeeded(content: str, elapsed_ms: int)`, `failed(user_msg: str, detail: str, elapsed_ms: int)`
   - Measure elapsed time in worker
   - Dependency: models.py, client.py
   - Acceptance: 成功/失敗の両経路で確実にシグナルが発火

- [x] Integrate worker into MainWindow
   - Start thread on send; connect signals to UI handlers
   - Lock/unlock UI around worker lifecycle
   - Show/hide wait indicator during sending
   - Acceptance: UI フリーズが発生しない。finally で必ず解除

- [x] Keybindings: Enter newline / Ctrl+Enter send
   - Add eventFilter to `QPlainTextEdit` to detect Ctrl+Enter
   - Keep Enter/Shift+Enter as newline
   - Acceptance: 要件どおりの送信/改行が作動し、空送信は防止

- [x] Auto-scroll to end
   - After user send and after assistant message append
   - Use `QTextCursor.End` and `ensureCursorVisible()`
   - Acceptance: 新規メッセージごとに末尾へスクロール

- [x] Markdown stylesheet adjustments
   - Apply base font, size, line height via `setStyleSheet`
   - Code blocks: monospace, background, padding, horizontal scroll
   - Inline code: subtle background
   - Acceptance: 読みやすさが向上し、長文でもレイアウト破綻しない

- [x] Error message mapping
   - Add function to map `LlmClientError`/HTTP-like info to user-friendly text
   - Use in worker UI failure path
   - Acceptance: 代表ケース（401/403/404/408/429/5xx/接続/パース）に対応

- [x] Config schema extension (minimal UI)
   - Extend `Config` with timeouts and UI flags from requirements（デフォルトのみ使用）
   - Pass request timeouts to `OpenAiCompatibleClient`（connect/read を適用可能なら対応）
   - Update `SettingsDialog` to expose timeout only（ms→秒換算など適切に）
   - Acceptance: 設定保存/読込が維持され、タイムアウトが反映

- [x] Logging/telemetry
   - Print start/end, elapsed_ms, error category
   - Keep surface minimal; future-proof for `logging`
   - Acceptance: 主要イベントが一貫した形式で出力

- [x] Tests
   - Unit test for error mapping function
   - Smoke test for client timeouts path if feasible
   - Acceptance: 重要ケースが赤にならない

## Out of Scope (confirm)
- Streaming rendering, cancel button, advanced scroll suppression, theme system

## Milestones
- M1: Worker + integration + keybindings
- M2: Auto-scroll + wait indicator + stylesheet
- M3: Config timeout + error mapping + logging
- M4: Tests and polish


