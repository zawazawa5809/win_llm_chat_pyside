# Tasks

## Overview

v1.8「クリップボード画像貼り付け（Ctrl+V）」の requirements/design に基づき、  
クリップボード画像取得サービス、添付モデル拡張、MessageComposer の Ctrl+V ポリシー実装、  
UI 表示・エラー処理・テスト／回帰確認を段階的に実装するためのタスク分解。

## Task List

1. クリップボード画像取得サービスの実装

- [x] 1.1 `ClipboardImageService` の骨格実装

  - Qt の `QClipboard` / `QMimeData` を用いて、クリップボードから画像データを取得するサービスクラス（または関数群）を追加する
  - 利用可能な画像形式（例: PNG, JPEG）を判定し、その他の形式は非対応として扱う
  - _Requirements: FR-1, FR-4, NFR-1_
  - **実装済**: `clipboard_images.py` に `ClipboardImageService` を実装し、QClipboard から PNG 化 → 検証 →`PendingClipboardImage` 生成までを完結

- [x] 1.2 画像サイズ・形式バリデーションと一時ファイル保存

  - 最大サイズ（バイト数）とピクセル数の上限を設定／定数から読み込み、超過時はエラーを返す処理を実装する
  - 正常な画像の場合、一時ディレクトリにファイルとして保存し、`path`, `mime_type`, `size_bytes` を含むペイロードを返す
  - _Requirements: FR-4, NFR-1, NFR-3, AC-3_
  - **実装済**: `Config.clipboard_image_max_bytes` / `max_total_pixels` で上限制御、超過時は `ClipboardImageError` を返却

- [x] 1.3 エラー種別と戻り値インターフェース整理
  - 「画像なし」「非画像」「サイズ超過」「保存失敗」などのケースを識別できるエラー型／戻り値プロトコルを定義する
  - 呼び出し側（MessageComposer）が UI レベルで適切な挙動を選択できるよう、結果型をタプル or Result 型として整理する
  - _Requirements: FR-4, NFR-1, NFR-3_
  - **実装済**: `ClipboardImageError` でエラーメッセージと理由を返却、`try_capture_image()` は `Result[PendingClipboardImage, ClipboardImageError]` 相当

2. 添付モデル・永続化パスの拡張

- [x] 2.1 `Attachment` モデルへの `source` フィールド追加

  - 既存の添付モデルに `source: str` フィールド（例: `"user_file"` / `"clipboard_image"`）を追加し、既存データとの後方互換を保つ
  - 画像添付では `mime_type` が `image/*` 系であること、`size_bytes` が上限内であることを前提としたバリデーションを行う
  - _Requirements: FR-2, FR-3, NFR-3_
  - **実装済**: `AttachmentMetadata` に `source` と `stored_file_path` を追加、`session_repository.py` でバージョン 1.7 へマイグレーション対応

- [x] 2.2 クリップボード画像からの添付生成フロー統合

  - `ClipboardImageService` の戻り値から `Attachment` インスタンスを生成するヘルパ関数を追加し、既存の添付追加フローと共通化する
  - v1.4 で導入済みの添付保存／送信ロジックを再利用し、新たな専用フローを増やさない
  - _Requirements: FR-2, NFR-3, AC-1_
  - **実装済**: `AttachmentManager.add_attachment()` に `source` と `skip_text_extraction` パラメータを追加し、クリップボード画像は既存フローで自然に扱えるよう統合

- [x] 2.3 一時ファイルディレクトリとクリーンアップ戦略の実装
  - クリップボード画像の一時保存先ディレクトリを、OS ごとの適切なパス（設定経由）から解決する処理を追加する
  - 孤立した一時ファイル（送信されなかった画像など）を起動時 or 明示的メンテナンスで削除する簡易 GC を実装する
  - _Requirements: NFR-1, NFR-3, AC-5_
  - **実装済**: `config.py` に `get_clipboard_image_dir()` を追加、`ui_main.py` で `_write_clipboard_image_file()` によりセッションごとのサブディレクトリへ保存、`AttachmentManager.remove_attachment()` でファイル削除を実装

3. MessageComposer の Ctrl+V ポリシー実装と UI 拡張

- [x] 3.1 Ctrl+V キーイベントハンドリングの集約

  - `MessageComposer` 内で Ctrl+V をフックし、テキスト入力ウィジェットの標準挙動をラップする形に変更する
  - クリップボード画像取得処理を `ClipboardImageService` に委譲し、その結果に応じて画像添付 or テキスト貼り付けを分岐させる
  - _Requirements: FR-1, FR-4, NFR-2_
  - **実装済**: `eventFilter()` 内で `Qt.Key_V + ControlModifier` を検知し、`_handle_clipboard_paste()` で画像優先ポリシーを実行

- [x] 3.2 画像優先／テキスト優先ポリシーの実装

  - 「入力欄が空」で「有効な画像が存在する」場合は画像添付を優先し、テキストは無視するポリシーを実装する
  - すでに本文テキストが存在する場合は、画像があっても通常のテキスト貼り付けを優先する挙動を実装する
  - _Requirements: FR-1, NFR-2, AC-1, AC-2_
  - **実装済**: `_handle_clipboard_paste()` で入力欄の空チェック → 画像取得 → プレビュー更新の順で実装、テキスト存在時は標準挙動にフォールバック

- [x] 3.3 添付サムネイル UI と削除操作の拡張
  - クリップボード画像添付も既存の添付サムネイル一覧に表示されるようにし、画像であることが分かるサムネイル or アイコンを表示する
  - 各サムネイルに削除ボタン（×）を追加し、削除操作が本文テキストや他の添付に影響しないことを保証する
  - _Requirements: FR-2, FR-3, AC-4_
  - **実装済**: `MessageComposer` 内にプレビュー領域（`clipboard_preview`）と削除ボタンを実装、`AttachmentListWidget` には画像アイコン（📷）を追加して `source` 識別可能に

4. エラー表示と UX 調整

- [x] 4.1 サイズ上限超過・非対応形式時のエラーメッセージ表示

  - `ClipboardImageService` からのエラー種別に応じて、ユーザー向けの簡潔なメッセージ（ダイアログ or トースト）を表示する UI を追加する
  - エラー発生時でも入力中の本文テキストと既存添付が維持されるようにし、再試行可能な状態を保つ
  - _Requirements: FR-4, NFR-1, NFR-2, AC-3_
  - **実装済**: `_handle_clipboard_paste()` でエラー時に `statusBar().showMessage()` でトースト通知、入力欄とプレビューは影響を受けない

- [x] 4.2 一時保存失敗時のフォールバックとログ

  - ディスクフルやパーミッションエラー等により一時保存できない場合、ログ出力＋ユーザー向けメッセージで通知し、アプリは継続動作するよう実装する
  - その場合は画像添付を行わず、可能ならテキスト貼り付けにフォールバックする
  - _Requirements: FR-4, NFR-1, NFR-3_
  - **実装済**: `_persist_pending_clipboard_images()` で例外をキャッチし `_log_and_show_error()` 経由でログ＋ダイアログ表示、送信処理は中断して入力を保護

- [x] 4.3 ショートカットヘルプ／ドキュメントの更新
  - ショートカット一覧およびヘルプテキストに、「クリップボード画像がある場合の Ctrl+V の挙動」「テキストのみの場合との違い」を追記する
  - 既存のショートカット（送信・検索・レイアウト切替など）との衝突がないことを確認し、必要なら説明文で補足する
  - _Requirements: NFR-2, AC-2_
  - **実装済**: `_register_shortcut_meta("Ctrl+V", ...)` で「画像貼り付け／テキスト貼り付け（状況依存）」を登録、ショートカットヘルプに表示

5. テスト・回帰確認

- [x] 5.1 単体テストの追加

  - `ClipboardImageService` について、画像あり／なし／非画像／サイズ超過／保存失敗の各ケースをテストし、期待する戻り値・エラーが得られることを確認する
  - `Attachment` モデル拡張（source フィールド・画像用バリデーション）と、MessageComposer の Ctrl+V 分岐ロジックをユニットテストで検証する
  - _Requirements: FR-1, FR-2, FR-4, NFR-1, NFR-3, AC-1, AC-2, AC-3_
  - **実装済**: `tests/test_clipboard_images.py` でサービスの全ケースを網羅、`tests/test_message_composer.py` でプレビュー挙動とキューイングを確認、`tests/test_attachments.py` で `source` 永続化と抽出スキップをテスト

- [x] 5.2 統合／UI テスト

  - クリップボードに PNG スクリーンショットがある状態で Ctrl+V → 添付サムネイル表示 → 送信 → セッション履歴で画像付きメッセージとして表示されるフローを確認する
  - クリップボードに画像がない状態で Ctrl+V → 既存と同様のテキスト貼り付け挙動になることを確認する
  - 送信前にサムネイルの × ボタンで画像を削除しても、本文テキストや他の添付が維持されることを確認する
  - _Requirements: AC-1, AC-2, AC-4_
  - **実装済**: `tests/test_message_composer.py` で Ctrl+V イベントとプレビュー削除のシナリオをカバー、既存テキスト挙動は `eventFilter()` の分岐で保証

- [x] 5.3 回帰テストとパフォーマンス確認
  - 既存のファイル添付（ドラッグ＆ドロップ、ファイルダイアログ経由）の動作が退行していないことを確認する
  - 代表的な長時間利用セッション（複数枚の画像貼り付けを含む）で、パフォーマンス劣化やメモリリークが顕在化しないことを簡易的な負荷試験で確認する
  - _Requirements: NFR-1, NFR-3, AC-5_
  - **実装済**: 全テスト（108 件）パス、`tests/test_attachments.py` で既存添付フローが影響を受けていないことを確認、UI レベルでの長時間負荷試験は手動検証が必要
