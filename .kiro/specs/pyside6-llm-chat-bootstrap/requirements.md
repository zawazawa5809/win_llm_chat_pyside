# Requirements Document

## Project Description (Input)

Windows 10/11 で動作する軽量な PySide6 製 LLM チャットクライアント。サーバ側 LLM（Ollama / OpenAI 互換など）に HTTP で接続し、単一 EXE（PyInstaller）で配布する。

## Scope

- インスコープ: PySide6 クライアント、HTTP 経由の LLM チャット、Markdown 表示、接続設定、最小限の起動中履歴
- アウトオブスコープ（v0.1）: ストリーミング表示、複数セッション、トレイ常駐、詳細な認証方式

## Functional Requirements

- FR-1 チャット送受信
  - 送信ボタンでユーザー入力を LLM エンドポイントへ送信できること
  - OpenAI 互換 `/v1/chat/completions` 形式をベースに抽象化すること
- FR-2 応答表示（Markdown）
  - レスポンス `content` を Markdown として描画できること
- FR-3 設定管理
  - ベース URL、モデル名、API キーを編集・保存・読込できること（ユーザープロファイル配下）
- FR-4 エラーハンドリング
  - 接続失敗や無効設定をユーザーに明確に通知し、アプリは継続すること
- FR-5 起動中履歴（最小）
  - 起動中のメッセージ履歴を画面で参照できること（終了でクリア許容）

## Non-Functional Requirements

- NFR-1 パフォーマンス
  - 起動完了目標 2.0 秒以内、常駐時メモリ 300MB 以下、アイドル時 CPU 数 %
- NFR-2 対応 OS / ランタイム
  - Windows 10/11、Python 3.11+、PyInstaller により単一 EXE 配布
- NFR-3 セキュリティ / プライバシー
  - 通信は HTTPS/HTTP のみ、API キーはユーザープロファイル配下に保存
- NFR-4 メンテナビリティ
  - PEP8、型ヒント、`requirements.txt` または `pyproject.toml` を整備、最低限のユニットテスト

## Architecture Constraints

- 同期 HTTP を既定（将来、非同期/スレッド化で拡張）
- `LlmClient` 抽象＋実装（OpenAI 互換/Ollama）で切り替え可能に
- GUI → アプリロジック → インフラの一方向依存を維持

## Acceptance Criteria

- 入力 → 送信 → レスポンスが Markdown で表示される
- 設定変更が保存・反映される（再起動後も読込）
- 代表的なエラーがユーザーに分かる形で通知され、アプリは継続

## Risks & Mitigations

- ネットワーク遅延や失敗: タイムアウトとリトライ戦略を設計可能にする余地
- API 仕様差異（Ollama vs OpenAI 互換）: 変換層を `LlmClient` 実装で吸収

## Out of Scope (v0.1)

- ストリーミング表示、複数セッション管理、常駐トレイ、強固な暗号化保存
