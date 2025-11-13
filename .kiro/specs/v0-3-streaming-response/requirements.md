# Requirements Document

## Project Description (Input)

@ROADMAP.md の v0.3 ストリーミング応答対応

## Requirements

### Scope

- インスコープ: LlmClient のストリーミング API 追加、HTTP ストリーム処理（OpenAI 互換＝ SSE 行単位、Ollama ＝ JSON Lines の双方）、UI の逐次更新と非ブロッキング化、任意の応答停止ボタン
- アウトオブスコープ（本仕様）: RAG・添付・Web 検索、包括的テーマ/アクセシビリティ最適化、複雑な再送制御

### Functional Requirements

- FR-1 ストリーミング API
  - `iter_chat(messages: list[Message]) -> Iterator[str]` を LlmClient に追加する
  - OpenAI 互換および Ollama ではストリーミングを必須実装とし、その他のエンドポイントでは非対応時に一括応答へフォールバックする
- FR-2 HTTP ストリーム処理
  - OpenAI 互換: `stream: true` + SSE 行を解析し `delta.content` を逐次抽出
  - Ollama: `stream: true` + JSON Lines を解析し `message.content` を逐次抽出、`done: true` で正常終了
  - ネットワーク/JSON エラー時は安全に終了し、UI 通知を行う
- FR-3 UI 逐次更新
  - アシスタントの最新メッセージへチャンクを追記表示する
  - QThread とシグナル/スロットによりメインスレッドをブロックしない
  - 任意で「応答停止」ボタンによりストリームを中断できる

### Non-Functional Requirements

- NFR-1 可用性/回復性: 例外はアプリを落とさず通知・後処理を保証する
- NFR-2 パフォーマンス: 長文でも UI フリーズを起こさないこと（8GB クラス PC 想定）
- NFR-3 設定と非ハードコーディング: タイムアウト等の閾値は設定層に集約し上書き可能
- NFR-4 ログ/トレース: ストリーム開始/終了/中断/エラーを軽量に記録（本文は保存しない）

### Configuration Keys（案）

- network.stream.connect_timeout_ms: number（例: 5000）
- network.stream.total_timeout_ms: number（例: 30000）
- ui.streaming.stop_enabled: bool（例: true）
- ui.streaming.chunk_render_interval_ms: number（例: 0〜16）

### Acceptance Criteria

- AC-1 対応エンドポイントでトークンが徐々に表示される
- AC-2 応答が長くても UI が固まらない
- AC-3 OpenAI 互換と Ollama の双方でストリーミング表示できる
- AC-4 エラー時にユーザー通知と後片付けが行われる
- AC-5 非対応エンドポイントでは一括応答に自動フォールバックする

### Out of Scope（将来）

- 同時複数ストリームの管理、きめ細かなバックプレッシャ、ネットワーク再接続戦略
