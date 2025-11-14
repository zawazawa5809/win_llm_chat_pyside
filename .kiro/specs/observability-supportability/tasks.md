# Tasks

## Overview

v0.6「観測性とサポート性」の requirements/design に基づき、軽量なローカルログ出力と診断情報ダイアログを、既存構造を崩さず段階導入するための実装タスク分解。

## Task List

1. ログ関連設定の追加と配線

- [x] 1.1 `Config` にログ/診断関連フィールドを追加
  - `logging.enabled: bool = True`
  - `logging.level: str = "info"`
  - `logging.dir: Optional[str] = None`（既定はアプリデータ配下の `logs` ディレクトリ）
  - `logging.max_file_size_mb: int = 5`
  - `logging.rotation_keep_files: int = 5`
  - `diagnostics.show_env_details: bool = False`
  - _Requirements: FR-2, FR-3, NFR-2, NFR-3_
- [x] 1.2 設定の読み書きとログディレクトリ解決を実装
  - `config.py` で既存設定との後方互換を維持しつつ、新フィールドを JSON に永続化
  - ログディレクトリ未指定時に OS 想定パス（例: `%APPDATA%/win-llm-chat-pyside/logs`）へフォールバック
  - _Requirements: FR-2, NFR-3_

2. AppLogger 実装（ファサード＋ローテーション）

- [x] 2.1 `app_logger.py` を新規作成し `AppLogger` を実装
  - Python 標準 `logging` を用いてファイルロガーを初期化（RotatingFileHandler 等）
  - ログフォーマットを `"{timestamp} {level} {event} {meta_as_json}"` の 1 行テキストとする
  - _Requirements: FR-1, FR-2, NFR-2, NFR-3_
- [x] 2.2 イベント/メタ情報 API を提供
  - `info(event: str, meta: dict)`, `error(event: str, meta: dict)` を提供
  - `logging.enabled` が false の場合はノップ、または最小限の内部状態のみ更新
  - _Requirements: FR-1, FR-3, NFR-2_
- [x] 2.3 センシティブ情報フィルタリングとログディレクトリ取得
  - `meta` からプロンプト本文・モデル応答・API キーなど禁止キーを除外
  - `get_log_dir() -> Path` でログディレクトリを返し、未作成時は必要に応じて作成
  - 例外発生時はアプリ動作を止めず、標準出力に警告を出す
  - _Requirements: FR-1, FR-2, FR-4, NFR-1, NFR-3_

3. UI/Worker からのログ呼び出し統合

- [x] 3.1 送信成功/失敗フローにログ呼び出しを追加
  - `MainWindow` / 送信 Worker で、成功時に `"chat.send.succeeded"`、失敗時に `"chat.send.failed"` を記録
  - メタ情報として `profile_name`, `elapsed_ms`, エラー種別/HTTP ステータス等を渡す
  - _Requirements: FR-1, AC-1, NFR-2, NFR-3_
- [x] 3.2 設定変更や起動/終了イベントのログ
  - プロファイル切替や設定保存時に `"config.updated"` などのイベントを記録
  - アプリ起動/終了時に `"app.start"`, `"app.exit"` を必要に応じて記録
  - _Requirements: FR-1, NFR-3_

4. 診断情報ダイアログと DiagnosticsInfoProvider

- [x] 4.1 `diagnostics.py` に `DiagnosticsInfoProvider` を実装
  - アプリバージョン（`pyproject.toml` 等）、Python バージョン、OS 情報、現在のプロファイル名などを収集
  - UI で貼り付けしやすい「キー=値」テキスト表現も生成
  - _Requirements: FR-5, NFR-3_
- [x] 4.2 UI に「診断情報…」メニューとダイアログを追加
  - メニューバー（例: ヘルプ）に「診断情報…」を追加し、クリックで Provider から情報取得→ダイアログ表示
  - テキスト全体をクリップボードへコピーできるボタン/ショートカットを実装
  - _Requirements: FR-5, AC-5_
- [x] 4.3 診断情報のプライバシー確認
  - 個人名・詳細パス等が含まれていないことを設計/実装レベルで確認
  - 必要に応じて masking/除外ロジックを追加
  - _Requirements: FR-5, NFR-1_

5. 「ログフォルダを開く」メニューの実装

- [x] 5.1 メニュー追加と OS エクスプローラ起動
  - メニューバーに「ログフォルダを開く」を追加し、クリックで `AppLogger.get_log_dir()` を呼び出し
  - Windows のファイルエクスプローラで該当フォルダを開く（`QDesktopServices` などを利用）
  - _Requirements: FR-4, AC-4_
- [x] 5.2 エラー時のユーザー通知
  - フォルダ取得やオープンに失敗した場合、簡潔なダイアログで通知し、詳細はログに記録
  - _Requirements: FR-4, NFR-3_

6. テストと検証

- [x]* 6.1 AppLogger の単体テスト
  - センシティブキー（プロンプト本文/API キー等）が出力されないこと
  - `logging.enabled` true/false で出力制御が効いていること
  - ローテーション設定が概ね期待通りに動作すること（小さなサイズで強制発火テスト）
  - _Requirements: NFR-1, NFR-2, NFR-3, AC-1, AC-2, AC-6_
- [x]* 6.2 DiagnosticsInfoProvider の単体テスト
  - 返却されるキーセットとフォーマットが仕様どおりであること
  - PII/不要なパスが混入しないこと
  - _Requirements: FR-5, NFR-1, NFR-3, AC-5, AC-6_
- [x]* 6.3 統合/手動シナリオ
  - 代表的な送信成功/失敗シナリオでログファイルが生成され、必要なメタ情報が含まれること
  - ログ ON/OFF 切替後の再起動で挙動が切り替わること
  - 「ログフォルダを開く」「診断情報…」が期待どおりに動作し、サポート担当がログ＋診断情報から原因のあたりを付けられること
  - _Requirements: FR-1〜FR-5, NFR-2, NFR-3, AC-1〜AC-5_

## Milestones

- M1: 設定拡張と AppLogger 基盤（1.x, 2.x）
- M2: UI/Worker からのログ呼び出し統合（3.x）
- M3: 診断ダイアログとログフォルダオープン UI（4.x, 5.x）
- M4: ログ/診断テスト・シナリオ整備（6.x）

## Out of Scope（確認）

- 中央集約ログ基盤や APM 連携、分散トレーシング
- モデル入出力の全文保存や RAG/添付/Web 検索との統合
- 高度なメトリクスダッシュボードやリアルタイム監視 UI


