# Implementation Plan

## Tasks

### 1. ドメインモデルと永続化拡張

- [x] 1.1 `AttachmentMetadata` モデルと `Session.attachments` の追加

  - `AttachmentMetadata`（id, session_id, filename, size_bytes, mime_type, page_count, text_length, status, error_message）を定義する
  - `Session` モデルに `attachments: list[AttachmentMetadata]` を追加し、JSON シリアライズ／デシリアライズ対応を行う
  - 既存セッション JSON に `attachments` が存在しない場合のデフォルト値（空リスト）を明確にする
  - _Requirements: R1, NFR-軽量_

- [x] 1.2 `SessionRepository` の添付対応拡張
  - `session_<id>.json` に `attachments` フィールドを保存／読み込みできるようにする
  - 旧バージョンのセッションファイルを壊さないよう、後方互換なマイグレーション（フィールド追加のみ）に留める
  - 抽出テキストを JSON に保存する場合の構造（例: `attachments_text`）を決定し、セッションスコープでのみ再利用されることを確認する
  - _Requirements: R1, NFR-軽量_

### 2. 添付管理ロジック（AttachmentManager）

- [x] 2.1 添付追加・削除・状態更新の実装

  - `add_attachment(file_path, session_id)` でファイルメタ情報を生成し、`attachments` に `status="pending"` で追加する
  - 添付削除 API（単一削除・全削除）を用意し、セッション保存時に反映されるようにする
  - UI から呼びやすいよう、添付 ID ベースの操作インターフェースを揃える
  - _Requirements: R1_

- [x] 2.2 抽出ジョブ起動と閾値チェック
  - 添付追加後、バックグラウンドで `FileTextExtractor` を呼び出すジョブを起動し、`status` を `extracting` → `ready` / `failed` に遷移させる
  - 抽出後に `text_length` を集計し、閾値を超えた場合はフラグを立てて UI 側で警告表示できるようにする
  - 抽出失敗時には `error_message` を記録し、再試行や削除操作でリカバリ可能な状態にする
  - _Requirements: R1_

### 3. ファイルテキスト抽出（FileTextExtractor）

- [x] 3.1 テキスト／Markdown ファイル対応

  - 文字コード検出を行ったうえで `*.txt` / Markdown からテキストを読み込む処理を実装する
  - 行数や文字数が極端に大きい場合のメモリ使用に注意し、必要に応じてチャンク読み込みを検討する
  - _Requirements: R1_

- [x] 3.2 PDF 抽出対応

  - 商用利用可能な軽量 PDF テキスト抽出ライブラリを選定し、依存追加する（`requirements.txt` / `pyproject.toml` 反映含む）
  - ページごとのテキスト抽出を行い、結合戦略（ページ区切りの改行など）を決める
  - 何ページ以上・何文字以上の場合に警告対象とするかのデフォルト値を決定する
  - _Requirements: R1_

- [x] 3.3 非対応形式・サイズ超過時の扱い
  - 非対応拡張子やサイズ上限超過ファイルを検出し、抽出を行わずに `status="failed"` と適切な `error_message` を設定する
  - UI 側でユーザーに分かるメッセージ（分割や形式変換の推奨）を出せるよう情報を揃える
  - _Requirements: R1_

### 4. 要約／Q&A プロンプト生成（AttachmentPromptService）

- [x] 4.1 要約テンプレート `file-summary-v1` の定義

  - `templates.json` に要約専用テンプレート `file-summary-v1` を追加し、見出し構造・文体・観点（概要／重要ポイント／TODO／リスク 等）を固定する
  - セッション RoleProfile と競合しない形で、「ファイル要約モード」の補助 system メッセージをテンプレ内に設計する
  - _Requirements: R2_

- [x] 4.2 Q&A テンプレート `file-qa-v1` の定義

  - `templates.json` に Q&A 用テンプレート `file-qa-v1` を追加し、「ファイル内容に基づいてユーザー質問に答える」ための指示を定義する
  - 回答フォーマット（箇条書き / セクション構造）や、回答できない場合の振る舞い（「不明」と明示）をテンプレ内で指定する
  - _Requirements: R2_

- [x] 4.3 `AttachmentPromptService` 実装
  - TemplateRepository から `file-summary-v1` / `file-qa-v1` を読み込み、ファイルメタ情報＋抽出テキストを埋め込んだ user メッセージを生成する
  - RoleProfileRepository から取得したセッションの system prompt を先頭に置き、必要に応じてファイル要約専用 system メッセージを追加する
  - 低温度などの LLM オプションを含むプロンプト契約オブジェクトを組み立てて `ChatController/Client` に渡す
  - _Requirements: R2_

### 5. UI 実装（AttachmentListWidget 他）

- [x] 5.1 添付一覧 UI の追加

  - `AttachmentListWidget` を実装し、ファイル名・サイズ・状態・警告アイコンなどを表示する
  - 「ファイルを添付」ボタンとドラッグ&ドロップハンドラを追加し、`AttachmentManager.add_attachment` を呼び出すフローを接続する
  - `status` や `error_message` に応じて、エラー／警告状態をアイコンとツールチップで表現する
  - _Requirements: R1_

- [x] 5.2 要約／Q&A アクション UI の追加
  - 各添付行に「要約」「質問する」ボタンを追加し、それぞれ `summarize(attachment_id)` / `ask_question(attachment_id, question)` を呼ぶようにする
  - 質問入力の UX（ダイアログ or インライン入力）を決め、既存チャット入力との混乱がないように設計する
  - 要約／Q&A 実行中はボタンを無効化し、完了後に再度有効化する
  - _Requirements: R2_

### 6. エラーハンドリング・ログ・テレメトリ

- [x] 6.1 ユーザー向けエラーメッセージ統一

  - 非対応形式・サイズ超過・抽出失敗などのメッセージ文言を整理し、ログメッセージと UI メッセージの対応を決める
  - 「何が起きたか」「ユーザーが次に何をすべきか」が分かる表現に統一する
  - _Requirements: R1, R2_

- [x] 6.2 ログ出力・診断情報の追加
  - 抽出失敗やサイズ超過などのイベントを、既存の `app_logger` / diagnostics に記録する
  - プロンプト本文は原則ログに出さないが、テンプレ ID やエラー種別などのメタ情報は記録してトラブルシュート可能な状態にする
  - _Requirements: NFR-軽量_

### 7. テスト計画

- [x] 7.1 ユニットテスト追加

  - `FileTextExtractor` の正常系・異常系テスト（ファイル種別ごと）を追加する
  - `AttachmentManager` の添付追加／状態遷移／閾値判定ロジックのテストを追加する
  - `AttachmentPromptService` のテンプレ適用とメッセージ生成（見出し構造や必須フィールドの存在）をテストする
  - _Requirements: R1, R2_

- [x] 7.2 結合・UI テストシナリオ
  - ファイル添付 → 抽出 → 要約リクエスト → 応答表示までの一連フローが成功するシナリオテストを追加する
  - 閾値超過ファイルで警告が表示されること、およびセッションを跨いで添付や抽出テキストが共有されないことを確認する
  - _Requirements: R1, R2, NFR-軽量_
