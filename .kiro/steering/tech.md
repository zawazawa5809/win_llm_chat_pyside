---
title: Tech Steering
description: 技術スタック・設計判断・運用方針をパターンとして保存する
updated_at: 2025-11-19
---

# 技術指針（Patterns）

## スタック（Stack）

- **言語**: Python 3.11+
- **GUI**: PySide6 (Qt6)
- **HTTP**: requests (同期) + ストリーミング処理
- **ビルド**: PyInstaller (One-file mode)
- **管理**: uv (依存解決・仮想環境)
- **構成**: Clean Architecture like (Features / Core / Services / UI)

## 主要な設計判断（Key Decisions）

### アーキテクチャ
- **Feature-based Packaging**: `features/` ディレクトリに機能ごとの Widget, Service, Repository をまとめる。
- **Core/Service 分離**: アプリ全体に関わる基盤 (`core/`) と外部連携 (`services/`) を明確に分ける。
- **Dependency Injection**: `factory.py` 等を通じて依存を注入し、テスト容易性を確保する。

### UI/UX 実装
- **同期 + Worker**: HTTP 通信は `services/workers.py` 内の QThread/Worker で行い、メインスレッドをブロックしない。
- **Theme Tokens**: 色やスタイルは `ui/styles/theme.py` で一元管理し、ハードコードを避ける。
- **Layout State**: ウィンドウ状態やサイドバー幅は設定ファイルに保存し、次回起動時に復元する。

### データ永続化
- **JSON Repository**: `SessionRepository` 等、データストアは JSON ファイルベースで実装（軽量・ポータブル）。
- **User Profile**: データ保存先は `%APPDATA%` 等のユーザー領域を使用。

### 観測性とエラー
- **Logging**: `core/app_logger.py` による構造化ログ。機密情報はフィルタリング。
- **Diagnostics**: `DiagnosticsDialog` で環境情報を収集・表示可能にする。
- **Exception Handling**: トップレベル (`core/app.py`) でキャッチし、クラッシュを回避してエラーダイアログを表示。

## 環境・運用
- **uv**: 高速な依存解決と venv 管理に使用。
- **GitHub Actions**: CI/CD パイプライン（Lint, Test, Build）。

## テスト方針
- `tests/` 配下に pytest を配置。
- ロジック（Repository, Service）の単体テストを重視。
- UI テストはスモークテスト（`pytest-qt` 利用）。
