# Tasks

## Overview

v0.3 ストリーミング応答対応（OpenAI 互換＝ SSE、Ollama ＝ JSON Lines）を最小公倍数設計で導入する。UI は逐次追記で非ブロッキング、未対応先のみ一括フォールバック。

## Task List

1. クライアント層のストリーミング IF 導入

   - [x] 1.1 `BaseLlmClient` に `iter_chat(messages)->Iterator[str]` を追加（Protocol/型整備）
     - FR-1
   - [x] 1.2 (P) OpenAI 互換: SSE 行解析で `delta.content` を逐次 yield（`stream=True` + `iter_lines`）
     - FR-2
   - [x] 1.3 (P) Ollama: JSON Lines 解析で `message.content` を逐次 yield（`done:true` で終了）
     - FR-2
   - [x] 1.4 非対応エンドポイント向けフォールバック（`send_chat()` を 1 回だけ yield）
     - FR-1

2. ワーカー層: ストリーミング実行経路

   - [x] 2.1 `StreamChatWorker` 追加（signals: `stream_chunk(str)`, `stream_finished(int)`, 既存 `failed(...)` 再利用）
     - FR-3, NFR-1
   - [x] 2.2 キャンセル機構（`_cancelled` フラグ、`cancel()` で停止、finally で後片付け）
     - FR-3, NFR-1

3. UI 統合と逐次描画

   - [x] 3.1 アシスタント空メッセージ先行追加、`stream_chunk` で追記表示、入力欄クリア条件整理
     - FR-3
   - [x] 3.2 応答停止ボタンの配置と有効/無効制御、キャンセル連携
     - FR-3
   - [x] 3.3 スクロール追従とレンダ間引き（必要時）、完了/失敗時の UI 復帰
     - FR-3, NFR-2

4. 設定と既定値の拡張 (P)

   - [x] 4.1 追加キー: `network.stream.connect_timeout_ms`, `network.stream.total_timeout_ms`, `ui.streaming.stop_enabled`, `ui.streaming.chunk_render_interval_ms`
     - NFR-3
   - [x] 4.2 バリデーション・既定値・クライアント/ワーカー配線
     - NFR-3

5. ログ/トレースとエラーメッセージ (P)

   - [x] 5.1 開始/終了/中断/例外の軽量ログ、ユーザー向け文言の維持
     - NFR-1, NFR-4

6. テストと手動シナリオ

- [x] 6.1 OpenAI SSE 解析の単体テスト（正常/途中中断/不正行）
  - FR-2
- [x] 6.2 Ollama JSONL 解析の単体テスト（正常/途中中断/不正行）
  - FR-2
- 6.3 手動 E2E（短文/長文/停止/エラー/非対応フォールバック）
  - FR-1, FR-3, NFR-2

7. 後方互換とドキュメント
   - [x] 7.1 `send_chat` 経路の維持・分岐確認、型/コメント整備
     - NFR-1, NFR-2

- [x] 7.2 README/運用メモ更新（設定キー・既知制約）
  - NFR-4
