---
title: API Standards
description: OpenAI 互換（SSE）と Ollama（JSON Lines）の運用基準をパターンとして保存する
---

# API 標準（Patterns）

## 対象スコープ（Scope）

- チャット補完系 API のクライアント実装指針
  - OpenAI 互換 `/v1/chat/completions`
  - Ollama `/api/chat`
- ストリーミング表示方針（SSE / JSON Lines）とフォールバック

## 共通原則（Common Principles）

- エンコードは UTF-8 を強制。誤報告時も `errors="replace"` 等で継続。
- ストリームの欠損/破損フレームはスキップ。致命でない限り全体停止を避ける。
- タイムアウトは接続/全体の双方を制御可能とし、失敗時は非ストリーミングへフォールバック。
- 秘密情報（API キー等）はログに出さない。トレースは簡潔に。

## OpenAI 互換（/v1/chat/completions）

- メソッド/エンドポイント
  - `POST {base_url}/v1/chat/completions`
- リクエスト（要点）
  - ヘッダ: `Content-Type: application/json`、任意で `Authorization: Bearer <API_KEY>`
  - ボディ: `{"model": "<name>", "messages": [...], "stream": <bool>}`
- 非ストリーミング応答
  - 200 OK 時に `choices[0].message.content` を抽出
- ストリーミング（SSE 風）
  - 本文は `data: {json}` 行。終端は `data: [DONE]`
  - `choices[0].delta.content` の増分を逐次反映
- エラー分類
  - 401/403 → AuthenticationError
  - その他非 200 → NetworkError（本文は短く添える）
  - JSON パース/想定外構造 → ResponseFormatError
  - Timeout/接続系 → NetworkError

## Ollama（/api/chat）

- メソッド/エンドポイント
  - `POST {base_url}/api/chat`
- リクエスト（要点）
  - ボディ: `{"model": "<name>", "messages": [...], "stream": <bool>}`
- 非ストリーミング応答
  - 200 OK 時に `message.content` を抽出
- ストリーミング（JSON Lines）
  - 各行が JSON。代表例: `{"message": {"role": "...", "content": "..."}, "done": false}`
  - `done: true` を受け取ったら終了
  - `message.content` の増分を逐次反映
- エラー分類
  - 非 200 → NetworkError
  - JSON パース/想定外構造 → ResponseFormatError
  - Timeout/接続系 → NetworkError

## 例外分類マッピング（Error Mapping）

- AuthenticationError: 認証/権限エラー（401/403）
- NetworkError: 接続・タイムアウト・非 200（認証除く）
- ResponseFormatError: 仕様上想定されるキー/配列が欠落・不正

## フォールバック方針（Fallback Policy）

- ストリーミング要求が失敗/非対応時は一括応答へフォールバックして UX を維持。
- フォールバック自体が失敗した場合のみ例外を上位へ伝播し、UI で通知。

## テスト/検証ポリシー（Testing Policy）

- リクエスト組み立て（ヘッダ/ボディ）とレスポンスの最小パースをユニットテスト化。
- 代表的な異常系（401/403、非 200、壊れたフレーム、空行多発）を再現テスト。

## 互換性とバージョニング（Compatibility）

- 実装は仕様に準拠しつつ寛容に解釈する（ロバストパース）。
- 破壊的変更が必要な場合は `LlmClient` 抽象を守り、実装差分で吸収。
