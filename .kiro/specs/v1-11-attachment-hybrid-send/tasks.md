# Implementation Plan

## Overview

v1.11「添付ハイブリッド送信（任意の添付を通常チャットに統合）」  
requirements/design に基づき、UI の選択状態管理・送信フロー拡張・ドメインロジック・設定・テストを段階的に実装するためのタスク分解。

## Task List

1. 添付選択 UI 拡張（AttachmentListWidget）

- [ ] 1.1 送信対象選択 UI の追加

  - `AttachmentListWidget` に「送信対象」列（チェックボックス）または行トグル UI を追加し、複数添付を同時選択可能にする
  - 選択状態はウィジェット内部でのみ保持し、セッション永続化には乗せない（送信後リセット前提）
  - 選択中かどうかが視覚的に一目で分かるスタイル（チェック状態／行ハイライトなど）を適用する
  - _Requirements: FR-1, NFR-1_

- [ ] 1.2 選択状態操作 API の実装

  - 現在選択されている添付の ID を返す `selected_attachment_ids()` を `AttachmentListWidget` に追加する
  - 送信完了後に選択状態をクリアするためのメソッド（例: `clear_selection_for_send()`）を実装する
  - 添付削除時には、該当 ID の選択状態が自動的に解除されるようにする
  - _Requirements: FR-1, FR-5, NFR-3_

- [ ] 1.3 「質問する」ボタンの廃止

  - `AttachmentListWidget` から「質問する」ボタンと関連シグナル `question_requested` を削除する
  - `MainWindow` の `_on_attachment_question` / `_send_attachment_prompt` など、質問専用フローに依存するコードを整理し、通常送信フローに一本化する
  - 既存テストで「質問する」ボタンを前提にしている箇所があれば更新または削除する
  - _Requirements: FR-4, FR-5_

2. MainWindow 送信フロー拡張

- [ ] 2.1 添付選択情報の取得と送信統合

  - `_on_send_clicked` にて、アクティブセッション ID とともに `attachment_widget.selected_attachment_ids()` を取得する処理を追加する
  - 選択された添付 ID が 0 件の場合は、現行と同じ「テキストのみ送信」フローを維持する
  - 選択された添付 ID が存在する場合は、後述の `AttachmentContextBuilder` に処理を委譲する
  - _Requirements: FR-2, FR-5_

- [ ] 2.2 送信完了後の選択状態リセット

  - ストリーミング完了コールバック（`_on_stream_finished` など）で、`AttachmentListWidget` に対して選択状態をクリアするメソッドを呼び出す
  - 失敗系（通信エラーなど）では選択状態を維持し、ユーザが再送できるようにする
  - 状態リセットのタイミングと例外ケースをテストでカバーする
  - _Requirements: FR-1, AC-2, AC-5_

- [ ] 2.3 添付付き送信時の UI 表示／ログ

  - 送信中ステータスバーやログに「添付付き送信」であること（添付件数や総文字数）を簡潔に記録する
  - トリミングが発生した場合には、ユーザ向けメッセージ（例: 「添付テキストが長いため一部を省略しました」）を表示し、`app_logger` にトリミングフラグを含めて記録する
  - _Requirements: FR-3, NFR-2_

3. Domain: AttachmentContextBuilder（新規）

- [ ] 3.1 コンテキスト生成ロジックの実装

  - `AttachmentContextBuilder`（関数 or クラス）を新規追加し、`session: Session`, `selected_ids: list[str]`, `config: Config` を入力として `AttachmentContextResult` を返す形にする
  - `session.attachments` と `session.attachment_texts` から、選択 ID に対応するメタ情報＋テキストを取得し、LLM 用のコンテキスト文字列を構築する
  - コンテキストフォーマット（ファイルごとの見出しやメタ情報の書き方）を設計し、将来変更しやすいよう 1 箇所に閉じ込める
  - _Requirements: FR-2, NFR-3_

- [ ] 3.2 文字数上限とトリミング戦略の実装

  - `config.attachment_send_max_chars`（仮）を参照し、添付テキストの総文字数が上限を超える場合のトリミング処理を実装する
  - トリミング戦略（ファイル単位でカットするのか、末尾を切るのか）を決め、`AttachmentContextResult(truncated=True)` に反映する
  - トリミング発生時には、どの程度の割合がカットされたか（例えば元文字数と残文字数）をログ用に返す
  - _Requirements: FR-3, NFR-2_

- [ ] 3.3 異常系・未抽出添付の扱い

  - `attachment_texts` にテキストが存在しない添付 ID はコンテキストから除外し、結果的に空コンテキストとなった場合には `truncated=False` かつ `text=""` を返す
  - `AttachmentContextBuilder` 内部で例外が発生した場合は、空コンテキストを返すようにし、呼び出し側で通常送信にフォールバックできる契約にする
  - _Requirements: FR-3, NFR-2, NFR-3_

4. Config 拡張とデフォルト値

- [ ] 4.1 添付付き送信関連設定の追加

  - `config.py` の `Config` に、添付付き送信専用の設定項目（`attachment_send_max_chars`, `attachment_send_truncate_notice_enabled` など）を追加する
  - デフォルト値を適切に設定し、既存の設定ファイルとの後方互換性を保つ（値が存在しない場合はデフォルトを用いる）
  - `load_config` / `save_config` が新しいフィールドを正しく扱うことを確認する
  - _Requirements: FR-3, NFR-2_

- [ ] 4.2 設定 UI / ドキュメントの反映（必要最低限）

  - 初期段階では設定 UI から編集できなくてもよいが、将来的に変更したくなる可能性が高い項目についてはコメントを残す
  - README や開発者向けドキュメントに、添付付き送信の文字数上限の存在と目的を簡潔に記載する
  - _Requirements: NFR-2_

5. 既存機能との整合性とクリーンアップ

- [ ] 5.1 AttachmentPromptService / 質問専用フローの整理

  - `AttachmentPromptService` と `MainWindow._send_attachment_prompt` 周辺を見直し、「要約」専用フローを残しつつ、「質問する」専用フローを削除または通常チャット利用に誘導する
  - 既存の要約テンプレート・QA テンプレートのうち、不要になるものがある場合は明示的に整理し、テストを更新する
  - _Requirements: FR-4, FR-5_

- [ ] 5.2 セッション切替・添付削除シナリオの確認

  - セッション切替時に、旧セッションで選択されていた添付選択状態が新セッションに漏れないことを確認する（UI のリフレッシュとリセットを実装）
  - 添付削除後に「幽霊選択状態」が残らないよう、選択状態の再構築処理を組み込む
  - _Requirements: FR-5, AC-5_

6. テスト計画と実装

- [ ] 6.1 ユニットテスト（AttachmentContextBuilder）

  - 添付 0 件／1 件／複数件・文字数が閾値未満／超過などのケースで、期待どおりの `AttachmentContextResult` が生成されることをテストする
  - テキスト未抽出添付が混在する場合に、それらが安全にスキップされることを確認する
  - 例外発生時に空コンテキストを返すフォールバックが機能することを確認する
  - _Requirements: FR-2, FR-3, NFR-3, AC-3_

- [ ] 6.2 メイン送信フローのテスト拡張

  - 既存の `test_streaming.py` / `test_client.py` 等を参考に、添付付き送信時に LLM に渡されるメッセージ（モック）が添付コンテキストを含むことを検証する
  - 添付なし／添付あり／トリミングありの 3 パターンで、エラーなくストリーミング応答が表示されることを確認する
  - _Requirements: FR-2, FR-3, FR-5, AC-1, AC-2, AC-3, AC-5_

- [ ] 6.3 UI / 回帰テスト

  - ユーザ視点のシナリオ（添付追加 → 選択 → 質問メッセージ送信 → 添付なしで雑談を継続）を通して、意図しない添付が送信されないことを手動テストする
  - `pytest` 全体実行で既存添付機能の回帰がないことを確認する（特に v1.4 / v1.9 関連テスト）
  - _Requirements: FR-1〜FR-5, NFR-1〜NFR-3, AC-1〜AC-5_
