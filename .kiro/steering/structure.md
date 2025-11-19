---
title: Structure Steering
description: ディレクトリ構成・命名・依存境界のパターンを保存する
updated_at: 2025-11-19
---

# 構造指針（Patterns）

## 組織化（Organization）

コードは `src/win_llm_chat_pyside/` 配下に集約し、機能・役割ごとに階層化する（Features / Layered Architecture）。

### ルート構造

- **`core/`**: アプリケーションの基盤。
  - `app.py`: エントリポイント実装。
  - `config.py`: 設定管理。
  - `factory.py`: DIコンテナ/ファクトリ。
  - `app_logger.py`: ログ基盤。
- **`features/`**: 機能単位のモジュール群（Vertical Slice）。
  - `chat/`: チャット機能（ビュー、入力、ストリーミング更新）。
  - `attachments/`: ファイル添付・抽出。
  - `prompts/`: テンプレート管理。
  - `roles/`: ロールプロファイル管理。
  - `sessions/`: セッション管理（UI/ロジック）。
  - `search/`: 検索機能。
- **`services/`**: インフラストラクチャ/外部連携。
  - `llm_client.py`: LLM API クライアント。
  - `storage.py`: ファイル永続化。
  - `global_hotkey.py`: ホットキー制御。
  - `workers.py`: 非同期ワーカー。
- **`ui/`**: プレゼンテーション層（共通部品・メインウィンドウ）。
  - `main_window.py`: アプリケーションシェル。
  - `styles/`: テーマ・CSS。
  - `dialogs/`: 共通ダイアログ。
- **`models/`**: ドメインモデル（DTO/Dataclass）。

### 機能モジュール（Features）の構成パターン

各 `features/xxx/` は可能な限り自己完結させる。

- `xxx_widgets.py`: UI コンポーネント。
- `xxx_services.py` / `xxx_repository.py`: ロジック・データアクセス。
- `xxx_dialogs.py`: 関連ダイアログ。

## 境界と依存（Boundaries）

1. **UI → Features/Core/Services**: UI は機能やサービスを利用する。
2. **Features → Services/Core**: 機能はインフラやコア機能を利用する。
3. **Services → Core**: サービスは設定やログなどのコア機能を利用する。
4. **Models**: どこからでも参照可（依存の末端）。

- **`ui/main_window.py`** はシェルであり、各 `features` のウィジェットを配置するコンテナとして振る舞う。具体的なビジネスロジックは持たない。
- **`config.py`** は他モジュールに依存しない。

## 命名とインポート（Naming & Imports）

- パッケージ構成に合わせた絶対インポートを推奨（例: `from win_llm_chat_pyside.core.config import ...`）。
- 相対インポートは同一パッケージ内のみ許容。
- クラス名は PascalCase、関数・変数は snake_case。

## UI パターン（UI Pattern）

- **コンポジション**: `MainWindow` は `MainLayoutContainer` を持ち、そこに `ChatWidget` や `SessionSidebar` などを注入・配置する。
- **テーマ**: `ui/styles/theme.py` の `ThemeTokens` で色・サイズを一元管理。

### ストリーミングと非同期

- `workers.py` の `StreamingWorker` 等でメインスレッドをブロックせずに実行。
- Signal/Slot で UI に結果を通知。

## 拡張ポイント（Extension Points）

- **新機能追加**: `features/` 配下に新ディレクトリを作成し、`ui/main_window.py` で統合。
- **LLM 対応**: `services/llm_client.py` に新規クライアントクラスを追加。
