# Tasks

## Overview

v1.5「軽量キーワード検索」の requirements/design に基づき、セッション内検索（Ctrl+F）、セッション一覧検索、添付テキスト検索、およびそれらを支える検索サービス・UI・テストを段階的に実装するためのタスク分解。

## Task List

1. ドメイン検索サービスの実装

- [x] 1.1 `SessionSearchService` の実装

  - `search_in_session(messages, keyword)` と `search_in_summaries(summaries, keyword)` を実装し、大文字小文字無視の単純部分一致でヒット位置／ヒットセッション ID を返す
  - 空文字や空白のみのキーワードはノーオペ or エラーとして扱う仕様を決め、呼び出し側の扱いと合わせる
  - _Requirements: FR-1, FR-2, NFR-1, NFR-2_

- [x] 1.2 `AttachmentSearchService` の実装
  - `{attachment_id, filename, text}` の配列に対して、キーワードヒットの有無と周辺抜粋（snippet）を含む `AttachmentHit` 配列を返す
  - 抜粋長と前後コンテキスト長を設定値または定数として切り出し、ハードコードを避ける
  - _Requirements: FR-3, NFR-1, NFR-2_

2. セッション内検索（Ctrl+F）UI の実装

- [x] 2.1 `SessionSearchBar` UI コンポーネントの追加

  - チャットビュー上部またはオーバーレイとして、キーワード入力フィールド＋ヒット件数表示＋次／前ボタンを持つ検索バーを実装する
  - Ctrl+F でバーを開き、ESC で閉じるショートカット処理を追加する
  - _Requirements: FR-1, NFR-3_

- [x] 2.2 ハイライト／スクロール連携の実装
  - `SessionSearchBar` から `SessionSearchService.search_in_session` を呼び出し、ヒット情報に基づいてメッセージビューのハイライトとスクロール位置を制御する
  - 検索バーを閉じた際にはハイライトと内部インデックス（現在位置）をクリアする
  - _Requirements: FR-1, NFR-2, NFR-3, AC-1_

3. セッション一覧検索の実装

- [x] 3.1 セッションサマリ取得 API の追加

  - `SessionRepository` に、セッション名＋冒頭数メッセージのプレーンテキストを返す軽量 API（例: `load_session_summaries()`）を追加する
  - 既存のメタデータロード処理と整合性を取りつつ、フルセッションロードを発生させないことを確認する
  - _Requirements: FR-2, NFR-1_

- [x] 3.2 `SessionListSearchBar` とフィルタリングの実装
  - セッション一覧ペインに検索入力フィールドを追加し、入力確定時にサマリを取得して `SessionSearchService.search_in_summaries` を呼び出す
  - ヒットセッションのみをリスト表示するモード、またはヒットバッジを付与するモードのどちらか（または両方）を実装し、UX を確認する
  - _Requirements: FR-2, NFR-2, NFR-3, AC-2_

4. 添付テキスト検索 UI（オプション）の実装

- [x] 4.1 `AttachmentSearchPanel` の追加

  - アクティブセッションに添付がある場合のみ表示される検索パネル（キーワード入力＋結果一覧）を追加する
  - 添付がない／未抽出の場合はパネルを非表示または無効状態表示とし、誤解を招かないようにする
  - _Requirements: FR-3, NFR-3_

- [x] 4.2 添付テキスト検索と LLM 補助プロンプト連携
  - `AttachmentSearchPanel` から `AttachmentManager` 経由で抽出済みテキストを取得し、`AttachmentSearchService.search_in_attachments` を呼び出す
  - 検索結果一覧から特定ヒットを選択したときに、snippet ＋キーワードを含む user メッセージを組み立てて `ChatController/Client` に送信するフローを実装する
  - _Requirements: FR-3, AC-3_

5. エラーハンドリング・パフォーマンス保護

- [x] 5.1 キーワードバリデーションと 0 件時メッセージ

  - 全検索 UI で、空文字やしきい値未満の短いキーワードに対する扱い（エラーメッセージ or 単純ノーオペ）を統一する
  - 0 件ヒット時には「該当なし」であることを明示し、UI が無反応に見えないようにする
  - _Requirements: NFR-2, NFR-3_

- [x] 5.2 重い検索のキャンセル／タイムアウト
  - メッセージ数・セッション数・添付テキストが想定より多い場合に備え、検索処理が UI を長時間ブロックしないように実装する（簡易なタイムアウトやバックグラウンド処理の検討含む）
  - 処理打ち切り時にはユーザー向けに「検索対象が大きすぎる」旨を通知する
  - _Requirements: NFR-1, NFR-2, AC-4, AC-5_

6. テストと検証

- [x] 6.1 ドメイン検索サービスのユニットテスト

  - `SessionSearchService` の正常系／0 件／大小文字無視などのテストケースを追加する
  - `AttachmentSearchService` のヒット抽出・抜粋生成ロジックについて、境界条件（先頭／末尾付近のヒットなど）を含めてテストする
  - _Requirements: FR-1, FR-2, FR-3, NFR-1, NFR-2_

- [ ]\* 6.2 UI／E2E テストシナリオ
  - セッション内検索で Ctrl+F → キーワード入力 → 次／前移動が期待どおり動作することを確認するシナリオを用意する
  - セッション一覧検索でヒットセッションが正しく絞り込まれ、選択からセッション遷移できることを確認する
  - 添付テキスト検索で、ヒットしたファイル名一覧と LLM への補助プロンプト送信が正しく機能することを手動または自動テストで検証する
  - _Requirements: AC-1, AC-2, AC-3, AC-4, AC-5_
