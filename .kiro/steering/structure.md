---
title: Structure Steering
description: ディレクトリ構成・命名・依存境界のパターンを保存する
---

# 構造指針（Patterns）

## 組織化（Organization）

- コードは `src/` 配下に集約し、役割ごとにモジュール分割する。
  - `app.py`: エントリポイント。例外の最上位ハンドリング。
  - `ui_main.py`: `MainWindow` と `SettingsDialog` を中心とした GUI。
  - `client.py`: `LlmClient` 抽象と実装（OpenAI 互換/Ollama）。
  - `config.py`: 設定の読み書き。ユーザープロファイル配下の JSON を既定とする。
  - `models.py`: ドメインモデル（例: `Message`）を dataclass で定義。
  - `storage.py`: 将来の履歴永続化用の最小枠。

## 境界と依存（Boundaries）

- GUI → アプリケーションロジック → インフラの一方向依存を維持。
- `ui_main.py` は `LlmClient` を注入され、HTTP 具体実装に依存しない。
- `config.py` は I/O に閉じ、呼び出し側に純粋な `Config` を返す。

## 命名とインポート（Naming & Imports）

- モジュールは責務ベースの短い英語名。クラス/関数は動詞/名詞句で可読性を優先。
- 相対 import は浅く保ち、循環依存を禁止。

## UI パターン（UI Pattern）

- チャット表示は Markdown 化して `QTextBrowser.setMarkdown()` で描画。
- 送信中はボタン無効化、完了後に有効化。ユーザー操作の可視性を優先。

## テスト配置（Tests）

- ユニットテストは `tests/` 配下。`client.py` のロジック中心に自動化。
- GUI はスモークテスト＋手動検証を基本とする。

## 拡張ポイント（Extension Points）

- `LlmClient` の実装追加、非同期化/スレッド化、履歴永続化、ストリーミング表示。
- 設定項目の拡充（プロキシ、タイムアウト等）は `Config` を起点に拡張。
