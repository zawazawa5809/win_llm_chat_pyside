# Tasks

## Overview

設計（Option C 初手：既存拡張）に基づき、最小変更で保存/ロード/エクスポート/上限警告を導入し、将来の責務分割に備える。

## Task List

1. Config スキーマ拡張（既定値で後方互換）

   - [x] 1.1 `Config` に history/export 項目を追加
     - `history_enabled: bool = True`
     - `history_format: Literal['json','markdown'] = 'json'`
     - `history_path: Optional[str] = None`（既定は `%APPDATA%/win-llm-chat-pyside/history/session.json`）
     - `history_max_messages: int = 400` / `history_max_chars: int = 200000`
     - `export_default_dir: Optional[str] = None` / `export_filename_pattern: str = "Chat-{yyyy-MM-dd HH-mm}.md"`
     - NFR-3
   - [x] 1.2 既存の `load_config` / `save_config` 互換維持（未知キーは無視）
     - NFR-1

2. storage.py の安全化と機能追加

   - [x] 2.1 `save_session_atomic(messages, path)` を実装（temp→`os.replace()`、`.bak` 1 世代保持）
     - FR-1, FR-8, NFR-2
   - [x] 2.2 `load_session_safe(path)` を実装（存在しない/不正 JSON 時の例外は呼出側でハンドリング可）
     - FR-2, NFR-2
   - [x] 2.3 `render_markdown(messages, metadata)` を実装（ユーザー/アシスタント区別、ヘッダに時刻・モデル・プロファイル名）
     - FR-4
   - [x] 2.4 `export_markdown_file(messages, path, metadata)` を実装
     - FR-3, FR-4
   - [x] 2.5 セッション保存時は資格情報が含まれないことを確認（混入可能性のあるフィールドは除外）
     - FR-9

3. UI 統合（`ui_main.py`）

   - [x] 3.1 起動時ロード: 設定と保存先から `load_session_safe`。失敗は新規開始＋情報ダイアログ
     - FR-2, NFR-2
   - [x] 3.2 終了時保存: `closeEvent` で `save_session_atomic`（必要なら Worker 化）
     - FR-1, FR-10
   - [x] 3.3 上限警告: 送信前/保存前に `messages` 数・総文字数を評価し非ブロッキング警告
     - FR-5, FR-6
   - [x] 3.4 メニュー: 「ファイル」→「この会話を Markdown で保存…」追加（`QFileDialog`、パターン適用）
     - FR-3, FR-4

4. 非ブロッキング I/O

   - [x] 4.1 既存の Worker 設計を流用し、必要に応じて保存/読み込み用 Worker を追加
     - FR-10, NFR-1

5. 既定保存先/パス決定

   - [x] 5.1 `config.get_config_path()` に倣いアプリデータ配下へ `history/session.json` 既定を導入
     - FR-7
   - [x] 5.2 パスが `None` の場合のフォールバックとディレクトリ作成
     - FR-7

6. テスト/手動シナリオ

   - [x] 6.1 原子的保存の単体テスト（temp→ 置換、破損時の `.bak` 復旧確認）
     - NFR-2
   - [x] 6.2 不正 JSON/読み込み失敗時の挙動確認（新規開始＋通知）
     - FR-2
   - [x] 6.3 Markdown 出力体裁（役割区別、メタ付与）の確認
     - FR-4
   - [x] 6.4 上限警告の境界値テスト（messages/chars）
     - FR-5, FR-6

## Milestones

- M1: Config 拡張 + storage 安全化（2.1/2.2/5.1/5.2）
- M2: UI 起動/終了フック + 上限警告（3.1/3.2/3.3）
- M3: Markdown エクスポート（2.3/2.4/3.4）
- M4: I/O 非ブロッキング + テスト（4.x/6.x）

## Out of Scope（確認）

- セッション複数管理、圧縮/検索、暗号化、RAG/添付/Web 検索は対象外（v1.0 後に検討）
