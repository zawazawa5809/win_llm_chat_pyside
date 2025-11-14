# Implementation Plan

## Task Format

- チェックボックスは実装進捗用。`(P)` は並行実行可を示す
- 要件トレーサビリティは `FR-*` ID を参照

### Work Breakdown

- [x] 1. プロファイル設定スキーマを導入（profiles 配列, current 名称） (P)

  - 設定モデルと永続層の読み書き追加（原子的保存, 一世代バックアップ）
  - バリデーション（重複名, 必須, 型, URL 体裁）
  - _Requirements: FR-1_

- [x] 1.1 既存単一設定からの自動移行を実装（冪等） (P)

  - 初回起動で profiles[0] を生成し current_profile_name を設定
  - ログに機微情報を出さない
  - _Requirements: FR-2_

- [x] 2. LlmClientFactory を実装しプロファイルに応じたクライアント生成

  - type=openai/ollama を切替、タイムアウト等は既定を踏襲
  - UI 側切替契機で再生成できるファクトリ API を提供
  - _Requirements: FR-5_

- [x] 3. メインウィンドウへプロファイル選択 UI を追加

  - 上部ドロップダウンで現在名を常時表示、選択時に Factory 経由で再生成
  - 送信中は切替 UI を disable、完了で enable
  - _Requirements: FR-3, FR-5_

- [x] 4. 設定ダイアログでプロファイル CRUD を実装

  - 追加/編集/削除、名称重複のバリデーション、確認ダイアログ
  - 保存後に MainWindow へ通知し再生成
  - _Requirements: FR-4_

- [x] 5. エラー処理とユーザー通知の実装

  - 入力エラーはフィールド別に表示、I/O 失敗は非致命ダイアログ＋ログ
  - 切替時エラーは現行クライアントを維持
  - _Requirements: FR-1, FR-3, FR-4, FR-5_

- [x] 6. テスト
  - Unit: Validator/Repository/Factory
  - Integration: CRUD→ 保存 → 再起動復元、切替時の送信ガード
  - E2E: 代表的な 2〜3 プロファイルで送受信スモーク
  - _Requirements: FR-1, FR-2, FR-3, FR-4, FR-5_

### Follow-up (Design Alignment)

- [x] 7. ProfileRepository 層の分離導入 (P)

  - 新規 `src/win_llm_chat_pyside/profile_repository.py` を作成（責務: load/save/migrate/validate）
  - 公開 API: `load() -> tuple[list[Profile], str]`, `save(profiles, current) -> None`, `migrate_if_needed(data: dict) -> Config`
  - _Requirements: FR-1, FR-2_

- [x] 7.1 config.py から移行/保存ロジックを移設 (P)

  - `_migrate_single_to_profiles_if_needed` と原子的保存を Repository に集約
  - `load_config()/save_config()` は Repository を呼ぶ薄い Facade に簡素化
  - _Requirements: FR-1, FR-2_

- [x] 7.2 影響箇所の依存修正（UI/Factory）

  - `ui_main.py` の設定読込/保存呼び出しを新 API へリダイレクト
  - 循環依存が発生しないよう import を最小化
  - _Requirements: FR-1_

- [x] 7.3 単体テスト追加

  - Repository: 読込/保存/冪等移行/バックアップ動作
  - 失敗系（壊れた JSON/書込失敗）のユーザーメッセージ検証
  - _Requirements: FR-1, FR-2_

- [x] 7.4 ドキュメント整合
  - `design.md` の Components を Repository 分離の実装に合わせ更新
  - 依存図・トレーサビリティ表を最新化
