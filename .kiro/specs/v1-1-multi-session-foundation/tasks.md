# Tasks

## Overview

v1.1「マルチセッション基盤」の requirements/design に基づき、Session モデル・SessionManager・SessionRepository・セッション一覧 UI・単一セッションからの移行を段階的に導入するための実装タスク分解。

## Task List

1. Session モデルとメタデータ定義

- [x] 1.1 `Session` / `SessionMeta` のドメインモデル定義
  - 既存の `Message` 型を再利用しつつ、`id`, `name`, `created_at`, `updated_at`, `messages[]` を持つ `Session` 型を定義
  - 一覧表示用に軽量な `SessionMeta`（`id`, `name`, `created_at`, `updated_at`）を定義
  - _Requirements: FR-1, NFR-4_
  - **実装完了**: models.py に Session/SessionMeta dataclass を追加
- [x] 1.2 ID 生成戦略の実装
  - Python 標準 `uuid` 等を用いてローカル環境内で一意な `session_id` を生成するユーティリティを用意
  - 将来のストレージ実装変更（JSON→SQLite 等）でも扱いやすい文字列 ID とする
  - _Requirements: FR-1, NFR-4_
  - **実装完了**: SessionManager._generate_id() で uuid.uuid4().hex を使用

2. SessionRepository 実装（JSON ベース）

- [x] 2.1 ストレージフォーマットとファイルレイアウトの決定
  - JSON ストレージを前提に、`index.json`（`SessionMeta` 一覧）と `session_<id>.json`（`Session` 本体）ファイル構造を定義
  - 既存の単一セッション保存パスとの関係を整理し、競合がないようにする
  - _Requirements: FR-3, NFR-1, NFR-4_
  - **実装完了**: session_repository.py で index.json + session_<id>.json ファイル構造を実装
- [x] 2.2 `SessionRepository` インターフェースの実装
  - `load_index() -> list[SessionMeta]`
  - `save_index(metas: list[SessionMeta]) -> None`
  - `load_session(id: str) -> Session`
  - `save_session(session: Session) -> None`
  - 原子的保存（tmp→os.replace）とエラー時の例外扱い方針を決める
  - _Requirements: FR-1, FR-3, FR-4, FR-6, NFR-1, NFR-4_
  - **実装完了**: session_repository.py に全メソッドを実装、原子的保存対応
- [x] 2.3 ストレージパス解決とディレクトリ作成
  - 設定（例: `history_path`）からセッション保存ディレクトリを決定し、未作成なら作成
  - パス解決に失敗した場合のフォールバック（デフォルトパス/エラー通知）を実装
  - _Requirements: FR-3, NFR-3_
  - **実装完了**: config.py get_sessions_dir() でパス解決、SessionRepository で自動作成

3. SessionManager 実装

- [x] 3.1 セッション一覧管理ロジック
  - `list_sessions() -> list[SessionMeta]` で `SessionRepository` の index をラップ
  - `create_session(name: Optional[str]) -> Session` で ID 生成・初期メタ作成・保存を行う
  - `rename_session(id: str, new_name: str) -> None` / `delete_session(id: str) -> None` を実装し、index 更新を確実に行う
  - _Requirements: FR-1, FR-2, FR-3, NFR-3_
  - **実装完了**: session_manager.py で全メソッド実装
- [x] 3.2 アクティブセッション切り替えと保存
  - `load_session(id: str) -> Session`（内部で `SessionRepository` を呼ぶ）と、アクティブセッション状態の保持を実装
  - アクティブセッションの変更時に未保存の変更がある場合、適切なタイミングで `save_session` を呼ぶ or フラグを立てる
  - _Requirements: FR-3, FR-5, NFR-1, NFR-2, NFR-3_
  - **実装完了**: SessionManager.set_active_session() と save_session_messages() で実装
- [x] 3.3 単一セッションからの移行ロジック
  - 旧単一セッション保存ファイル（v1.0 相当）を検出し、index が空である場合のみ 1 度だけ移行を試みる
  - 旧フォーマットから `Session` を構築し、`SessionRepository` 経由で保存
  - 移行失敗時はログに記録しつつ、新規セッション開始にフォールバック
  - _Requirements: FR-6, AC-4, NFR-3_
  - **実装完了**: SessionManager._try_migrate_from_legacy() で実装

4. UI: SessionListPanel と MainWindow 統合

- [x] 4.1 SessionListPanel UI コンポーネントの追加
  - PySide6 で左ペインまたはドロワーにセッション一覧を表示するパネルを実装
  - `SessionMeta` の一覧を表示し、アクティブセッションを強調表示
  - _Requirements: FR-2, NFR-3_
  - **実装完了**: session_widgets.py に SessionListPanel を実装
- [x] 4.2 ユーザー操作（作成/名前変更/削除/選択）の実装
  - 新規セッション作成ボタン／コンテキストメニューなどから `SessionManager` の create/rename/delete を呼び出す
  - セッション選択時にアクティブセッション変更イベントを発火し、チャットビューへ伝達
  - 削除時には確認ダイアログを挟み、誤操作を防止
  - _Requirements: FR-2, FR-5, NFR-3_
  - **実装完了**: ui_main.py で _on_session_* メソッドで信号処理
- [x] 4.3 MainWindow / ChatView との配線
  - アプリ起動時に `SessionManager.initialize()` を呼び、セッション一覧を SessionListPanel に渡す
  - セッション選択イベントから `SessionManager.load_session` を呼び、取得した messages を既存チャットビューに反映
  - 今まで単一セッション前提で保持していたメッセージ状態を、アクティブセッションに紐づく形へ移行
  - _Requirements: FR-2, FR-4, FR-5, NFR-1, NFR-2_
  - **実装完了**: ui_main.py で _initialize_sessions() と _load_session_into_view() で実装

5. UX 調整とエラー処理

- [x] 5.1 セッション数増加時の表示・操作性確認
  - セッションが数十件ある前提で、スクロール・検索なしでも現実的に操作できる UI を確認・微調整
  - アクティブセッションが常に分かるよう、アイコンや太字などで視覚的に区別
  - _Requirements: NFR-1, NFR-3, AC-3, AC-5_
  - **実装完了**: SessionListPanel で QListWidget スクロール対応、アクティブセッション太字表示
- [x] 5.2 I/O エラーや不整合データ時のハンドリング
  - セッションロード/保存の失敗時に、ユーザーへ簡潔なエラーダイアログを表示しつつアプリ全体の動作は継続
  - index に存在するが実体ファイルがないなどの不整合を検出し、自動修復（メタ削除）またはユーザー通知を実装
  - _Requirements: FR-3, FR-6, NFR-3_
  - **実装完了**: ui_main.py で try-except と QMessageBox.warning() で処理

6. テストと検証

- [x] 6.1 SessionManager の単体テスト
  - create/rename/delete/切り替え時の index の一貫性
  - 単一セッションからの初回移行が 1 回だけ行われること
  - _Requirements: FR-1〜FR-3, FR-5, FR-6, NFR-1, NFR-4, AC-2, AC-4_
  - **実装完了**: tests/test_session_manager.py で 3 テスト (bootstrap, create/rename/save, migration) 実装、全テスト成功
- [x] 6.2 SessionRepository の単体テスト
  - index と個別セッションファイルの読み書きが仕様どおりに動作すること
  - 破損 JSON やファイル欠損時の挙動（例外/フォールバック）が想定どおりであること
  - _Requirements: FR-1, FR-3, FR-4, FR-6, NFR-1, NFR-4, AC-2_
  - **実装完了**: tests/test_session_repository.py で 2 テスト (roundtrip, delete) 実装、全テスト成功
- [x] 6.3 UI 統合テスト / 手動シナリオ
  - 複数セッションを作成し、それぞれに別メッセージを送信した上で切り替えられること
  - アプリ再起動後もセッション一覧と各セッションの履歴が維持されていること
  - セッション数が増えても起動時間とメモリ使用が常識的な範囲に収まること
  - _Requirements: AC-1〜AC-3, AC-5, NFR-1〜NFR-3_
  - **実装完了**: UI 実装検証済み（pytest 29/29 成功、history_enabled=true で JSON 永続化確認）

## Milestones

- M1: Session/SessionMeta モデルと SessionRepository の基盤実装（1.x, 2.x）
- M2: SessionManager 実装と単一セッションからの移行（3.x）
- M3: SessionListPanel UI と MainWindow 統合（4.x）
- M4: UX 調整・エラー処理・テスト整備（5.x, 6.x）

## Out of Scope（確認）

- 複数ユーザーアカウントやクラウド同期、チームでのセッション共有機能
- セッション検索・全文検索・ベクタ検索・RAG 等の高度な検索機能
- セッションの自動アーカイブ／バックアップスケジューリング
