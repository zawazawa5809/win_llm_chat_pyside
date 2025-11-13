# Design Document

## 概要

v0.3「ストリーミング応答対応」により、LLM 応答の体感速度と操作性を高める。まずは「1 方式」に絞って堅実に実装し、将来の拡張（別方式・高度な制御）に備える。

## スコープと非スコープ（設計観点）

- スコープ
  - クライアント層にストリーム API を追加（フォールバックあり）
  - HTTP ストリーム処理（OpenAI 互換＝ SSE 行単位、Ollama ＝ JSON Lines）を双方実装
  - UI はチャンクを逐次追記、メインスレッドをブロックしない
  - 任意の「応答停止」操作（キャンセル）
- 非スコープ
  - 同時複数ストリーム、バックプレッシャ、再接続戦略の最適化
  - RAG/添付/Web 検索等の周辺機能

## アーキテクチャ

- レイヤ分離
  - ドメイン: `models.Message`
  - クライアント: `client.BaseLlmClient` 実装（OpenAI 互換/Ollama）
  - UI/アプリ: `ui_main.MainWindow`、`workers.ChatWorker`（QThread）
- ストリーミング経路
  1. UI が送信を開始 → Worker スレッド起動
  2. Worker が `client.iter_chat(messages)` を反復
  3. 受信チャンクを Signal 経由で UI に通知
  4. UI はアシスタントの最新メッセージに追記表示
  5. 完了/中断/エラーを確実に後処理

## インターフェース設計（Client 層）

- 既存
  - `BaseLlmClient.send_chat(messages: list[Message]) -> str`
- 追加
  - `BaseLlmClient.iter_chat(messages: list[Message]) -> Iterator[str]`
    - 対応エンドポイント: ストリームで断片テキストを順次返す
    - 非対応エンドポイント: 内部で `send_chat` を呼び出し、全文を 1 回だけ yield するフォールバック
- OpenAI 互換
  - `POST /v1/chat/completions` に `stream: true`
  - `requests.post(..., stream=True)` で行単位を取り出し、`data: ...` の SSE を解析
  - `choices[].delta.content` を抽出して逐次 yield
- Ollama（必須）
  - `POST /api/chat` に `stream: true`
  - JSON Lines を逐次受信し、各行の `message.content` を差分として逐次 yield
  - `done: true` を受信したら正常終了として扱う

## エラー・例外設計

- ネットワーク/認証/形式エラーは既存の例外階層（`NetworkError`, `AuthenticationError`, `ResponseFormatError`）を再利用
- ストリーム中の例外は即座に終了し、UI へ `failed` Signal として伝達
- finally 相当でクリーンアップ（接続破棄/フラグ解除/フォーカス戻し）を保証

## スレッド/シグナル設計（UI 層）

- 追加 Signal（`workers.ChatWorker` へ）
  - `stream_started()`（任意）
  - `stream_chunk(str)`
  - `stream_finished(int elapsed_ms)`
  - `failed(str user_message, str detail, int elapsed_ms)`（既存流用）
- ワーカー処理
  - `run_stream()` を新設（既存の `run()` は一括応答用として残す）
  - キャンセル用フラグ `self._cancelled` を持ち、外部から `cancel()` で中断
- UI 側
  - 送信開始時に「アシスタントの空メッセージ」を追加し、`stream_chunk` で追記
  - 自動スクロールは設定に従い実行
  - 応答停止ボタン（任意）を押下で `cancel()` シグナル送出

## 設定項目（追加案）

- `network.stream.connect_timeout_ms`（初期 5000）
- `network.stream.total_timeout_ms`（初期 30000）
- `ui.streaming.stop_enabled`（初期 true）
- `ui.streaming.chunk_render_interval_ms`（0〜16ms、レンダリング間引き用）

## フォールバック戦略

- `iter_chat` 未対応（または API 非対応）時は `send_chat` の結果を 1 回だけ返す
- OpenAI 互換・Ollama に対しては本フォールバックは用いない（双方ストリーミング必須）
- UI は逐次更新/一括更新の両方に対応する描画経路を持つ（実装時に分岐）

## 移行影響

- 既存 UI の送信フローに「ストリーム経路」を追加
- 既存 `ChatWorker` は後方互換のため残置し、新規 `StreamChatWorker`（仮）を追加して段階導入
- 例外文言・ログは既存ポリシーを継承

## テスト観点

- 正常系: 短文/長文/途中改行/Unicode/高速/低速
- 異常系: 接続失敗/認証失敗/形式不正/途中切断/キャンセル
- UX: フリーズ無し、スクロール追従、停止ボタンの即応性

## 将来拡張

- SSE/JSONL の両対応、プロファイル単位で方式切替
- トークン単位のレイテンシ計測、ストリーム再接続
