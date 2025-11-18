# Implementation Plan

## Overview

v1.12「チャットビュー左右レイアウト＆バブルデザイン」の requirements/design に基づき、  
新チャットビュー（BubbleChatView）導入、テーマトークン拡張、検索／スクロール連携、  
回帰リスクを抑えた段階的移行を行うためのタスク分解。

## Task List

1. 新チャットビュー骨格（BubbleChatView / Model / Delegate）

- [x] 1.1 MessageListModel の追加

  - `QAbstractListModel` を継承した `MessageListModel` を新規追加し、既存の `Message` リストを保持・公開する
  - `role` / `content` / `created_at` / 添付情報などを `Qt.UserRole` 以降のカスタムロールで提供する
  - 追加・更新・クリア操作に対し、最小限の `rowsInserted` / `dataChanged` / `modelReset` シグナルを発行する
  - _Requirements: FR-1, FR-2, FR-3, FR-4, NFR-3_

- [x] 1.2 MessageItemDelegate による左右バブル描画

  - `QStyledItemDelegate` を継承した `MessageItemDelegate` を実装し、User=右/Assistant=左/System=中央寄せのバブルレイアウトを描画する
  - 連続する同一ロールのメッセージでは上下余白や角丸を調整し、会話のまとまりが視覚的に分かるようにする
  - 本文テキストに加え、コードブロックや添付プレースホルダをバブル内部に整然と配置する（描画だけ先に整える）
  - _Requirements: FR-1, FR-2, FR-3, FR-4, NFR-1, NFR-3_

- [x] 1.3 BubbleChatView コンテナの実装

  - 内部に `QListView`＋`MessageListModel`＋`MessageItemDelegate` を持つ `BubbleChatView` を新規追加する
  - `set_messages(list[Message])` / `append_message(Message)` / `update_last_message(str)` など、現行 `_update_chat_view` と互換性のある API を整える
  - 自動スクロール指示を `ChatScrollController` と協調させるためのフック（末尾インデックス通知など）を用意する
  - _Requirements: FR-1, FR-2, FR-3, FR-4, NFR-1, NFR-3_

2. テーマトークン拡張とバブルスタイル適用

- [x] 2.1 ThemeTokens / ThemeRole の拡張

  - `theme.py` の `ColorTokens` / `SpacingTokens` にバブル用トークン（user/assistant/system 背景色・テキスト色、バブル内外余白など）を追加する
  - 必要に応じて `ThemeRole` に `CHAT_BUBBLE_USER` / `CHAT_BUBBLE_ASSISTANT` / `CHAT_BUBBLE_SYSTEM` / `CHAT_META` を追加し、役割ごとの意味づけを明確にする
  - 既存トークンとの後方互換性を保ちつつ、新トークン未使用状態でも既存 UI が壊れないデフォルト値を設定する
  - _Requirements: NFR-1, NFR-2_

- [x] 2.2 Delegate へのテーマ適用

  - `MessageItemDelegate` でバブル背景色・テキスト色・メタ情報色・枠線・角丸・余白をすべてテーマトークン経由で取得するようにする
  - 既存の `chat_view.setStyleSheet(...)` でハードコードされていたチャット背景・文字色をトークン利用に寄せ、重複スタイルを整理する
  - 暗い背景でも可読性が維持されるよう、メタ情報は本文より控えめだが十分なコントラストを持つ色で表示する
  - _Requirements: FR-2, NFR-1, NFR-2_

3. MainWindow との統合と段階的移行

- [x] 3.1 ChatViewStack（旧ビューと新ビューのカプセル化）

  - `MainWindow` 直下に新しいチャットビューを差し込む前段として、`QTextBrowser` ベースの既存ビューと `BubbleChatView` をカプセル化する `ChatViewStack`（または同等クラス）を導入する
  - 初期段階では内部的に旧ビューを利用しつつ、API は `BubbleChatView` と一致させておく（切り替えを容易にする）
  - デバッグ用途として「旧ビュー／新ビュー切り替えフラグ」を設け、レイアウト崩れや性能問題の切り分けを可能にする
  - _Requirements: NFR-3, AC-4_

- [x] 3.2 `_update_chat_view` 経路の差し替え

  - `MainWindow._update_chat_view` およびストリーミング関連コードを、`ChatViewStack` 経由で `BubbleChatView` を更新するようリファクタリングする
  - 送信・ストリーミング・セッション読み込み・クリアなど全てのパスで、新チャットビューが一貫して使われることを確認する
  - 検索ハイライト処理（`setExtraSelections` など）を新チャットビュー側に移し、旧ビュー固有の実装から切り離す
  - _Requirements: FR-1〜FR-4, NFR-3, AC-4_

4. 検索・スクロール・アクセシビリティ連携

- [x] 4.1 セッション検索サービスとの統合

  - `SessionSearchService` が返すヒット情報（メッセージインデックス＋テキスト範囲）を `BubbleChatView` で扱える形に変換する
  - `BubbleChatView` に `highlight_hits(hits)` / `focus_hit(index)` などの API を追加し、既存のセッション内検索 UI から利用する
  - 検索ジャンプ後も左右レイアウトとグルーピングが破綻しないよう、スクロール位置と選択状態の更新を慎重に実装する
  - _Requirements: FR-3, NFR-1, NFR-3_

- [x] 4.2 ChatScrollController の対応拡張

  - `ChatScrollController` を `BubbleChatView` に対応させ、末尾への自動スクロールや「ユーザーが手動でスクロールした際に自動スクロールを抑制する」ポリシーを維持する
  - ストリーミング時の増分追記でも、スクロールジャンプやチラつきが発生しないよう調整する
  - _Requirements: NFR-1, NFR-3, AC-2_

5. テスト・リグレッション・視覚検証

- [x] 5.1 モデル／デリゲート単体テスト

  - `MessageListModel` の追加・更新・クリアに関するテストを追加し、期待どおりのデータ整合性とシグナル発行が行われることを確認する
  - `MessageItemDelegate` の `sizeHint` がメッセージ長・ウィンドウ幅に応じて単調増加することをテストし、極端な長文や空メッセージでも破綻しないことを確認する
  - _Requirements: FR-1〜FR-4, NFR-1, NFR-3, AC-1, AC-2_

- [x] 5.2 MainWindow 統合テスト／UI テスト

  - 代表的な会話シナリオ（User/Assistant/System 交互＋長文＋コード＋添付）を対象に、左右バブルレイアウト・メタ情報表示・スクロール挙動が要件通りであることをテストする
  - 既存のストリーミングテスト・検索テストに、新チャットビュー前提のケースを追加し、旧実装との回帰差分を確認する
  - _Requirements: FR-1〜FR-4, NFR-1〜NFR-3, AC-1〜AC-5_

- [x] 5.3 手動／視覚レビューと旧ビュー削除

  - 24 インチ半画面想定のレイアウトで、長時間の読書・コードレビューに耐えうるかを実機確認し、色・余白・フォントを微調整する
  - 旧 `QTextBrowser` ベースのチャットビューコードを段階的に削除し、使用されなくなったスタイルやヘルパを整理する
  - _Requirements: NFR-1, NFR-2, NFR-3, AC-1〜AC-4_
