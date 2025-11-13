# Design Document

## Overview
Windows 10/11 向けの軽量 PySide6 クライアント。GUI・アプリロジック・インフラを分離し、`LlmClient` 抽象で接続先差異（OpenAI 互換 / Ollama）を吸収する。同期 HTTP を既定とし、将来の非同期化/スレッド化を許容する。

## Architecture
```text
[User]
  ↓
[PySide6 GUI (MainWindow, SettingsDialog)]
  ↓
[ChatController / ChatSession]
  ↓ (calls)
[LlmClient interface]
  ├── OpenAiCompatibleClient
  └── OllamaClient (optional)
  ↓
[HTTP Endpoint]
```

### Modules and Responsibilities
- app.py
  - エントリポイント。`QApplication` 起動、未処理例外のトップレベルハンドリング
- ui_main.py
  - `MainWindow`: チャットビュー表示、入力、送信トリガ、状態管理（送信中の disable など）
  - `SettingsDialog`: base_url / model / api_key の編集と保存
- client.py
  - `Protocol BaseLlmClient` or ABC
    - `send_chat(messages: list[Message]) -> str` を定義
  - `OpenAiCompatibleClient`: `/v1/chat/completions` を叩き、レスポンスから content を抽出
  - `OllamaClient`（任意）: `/api/chat` に適合するようボディ/レスポンス変換
- config.py
  - `Config` dataclass と `load_config` / `save_config`
  - 保存場所は `%APPDATA%/win-llm-chat-pyside/config.json`（既定）
- models.py
  - `Message` dataclass（role, content）
- storage.py
  - v0.1 は枠のみ（将来の履歴永続化を見据えた最小 API）

## Key Flows
### Send Message
1) `MainWindow` が入力を `Message(role="user")` に変換し内部リストへ追加  
2) Markdown へ整形してビュー更新  
3) `LlmClient.send_chat(messages)` を同期呼び出し  
4) 応答文字列を `Message(role="assistant")` として追加  
5) 再度 Markdown 生成しビュー更新  
6) 送信中はボタン disable、完了後 enable

### Settings
- `SettingsDialog` で値編集 → `save_config` → `MainWindow` 側で反映（必要に応じて `LlmClient` 再生成）
- バリデーション: URL 形式、必須項目、タイムアウト値（将来拡張）

## HTTP Contract
### OpenAI 互換（baseline）
Endpoint: `{base_url}/v1/chat/completions`  
Request body (要旨):
```json
{
  "model": "<model>",
  "messages": [{"role":"user","content":"..."}]
}
```
Response (要旨):
```json
{ "choices":[{ "message": { "role":"assistant", "content":"..." } }] }
```
抽出: `choices[0].message.content`

### Ollama（option）
Endpoint: `{base_url}/api/chat`  
クライアント実装内で OpenAI 互換との相互変換を行う。

## Error Handling
- ネットワーク/認証/フォーマットに大別し、ユーザーに意味あるメッセージを表示
- 例外は GUI まで未処理で伝播させない。ログは簡潔に
- タイムアウト/リトライは実装で調整可能に（デフォルトは保守的）

## UI Details
- 表示: `QTextBrowser.setMarkdown()` を用いる
- 入力: `QPlainTextEdit`、改行と送信ボタンを併用
- 状態: 送信中の UI 制御、エラーダイアログ表示

## Extensibility
- `LlmClient` 実装追加（Anthropic 互換など）
- ストリーミング表示: `QThread` or `async` 併用で逐次更新
- 履歴永続化: `storage.py` の具体化（ローテーション/検索）
- 設定拡張: プロキシ、タイムアウト、証明書検証、モデル候補プリセット

## Non-Functional Strategy
- 起動時間短縮: 遅延初期化（クライアント生成は初回送信時でも可）
- メモリ: 不要オブジェクトの開放、履歴は必要最小限で描画
- テスト: `client.py` のユニットテスト、UI はスモーク＋重要ロジック分離

## Open Questions
- ストリーミング表示の UX（キャンセル/中断操作）
- 認証方式のバリエーション（社内仕様差）


