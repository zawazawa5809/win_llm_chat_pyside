---
title: API Standards
description: OpenAI 互換（SSE）と Ollama（JSON Lines）の運用基準をパターンとして保存する
updated_at: 2025-11-19
---

# API 標準（Patterns）

## 対象スコープ（Scope）

- チャット補完系 API のクライアント実装指針
  - OpenAI 互換 `/v1/chat/completions`
  - Ollama `/api/chat`
- ストリーミング表示方針（SSE / JSON Lines）とフォールバック

## 共通原則（Common Principles）

- **UTF-8 強制**: エンコードは UTF-8 を明示。
- **Robust Parsing**: 欠損/破損フレームはスキップし、全体停止を避ける。
- **Timeout**: 接続タイムアウトとリードタイムアウトを個別に設定可能にする。

## 実装詳細（Implementation）

### OpenAI 互換 (`/v1/chat/completions`)
- **Request**: `{"model": "...", "messages": [...], "stream": true/false}`
- **Streaming (SSE)**:
  - `data: {...}` 行をパース。
  - `[DONE]` で終了。
  - `choices[0].delta.content` を取得。

### Ollama (`/api/chat`)
- **Request**: `{"model": "...", "messages": [...], "stream": true/false}`
- **Streaming (JSON Lines)**:
  - 行ごとの JSON オブジェクト。
  - `done: true` で終了。
  - `message.content` を取得。

## エラーハンドリング

1. **NetworkError**: 接続不能、タイムアウト。
2. **AuthenticationError**: 401/403。
3. **ResponseFormatError**: JSON パース失敗、期待するキーの欠落。

- **フォールバック**: ストリーミング失敗時は、可能なら非ストリーミング（一括取得）を試行するロジックを検討（必須ではないが推奨）。

## ログ・セキュリティ
- API キーはログに出力しない（`[FILTERED]`）。
- プロンプト内容もログレベルによっては省略する。
