# Tasks

## Overview

v1.7「UX 一貫性と操作性の磨き込み」の requirements / design に基づき、  
検索 UI パターン統一、ショートカット整理、テンプレート／役割／添付の導線最適化、  
フォーカス／スクロール挙動の統一、およびテスト／ドキュメント整備を段階的に実装するためのタスク分解。

## Task List

1. 検索 UI パターン統一（SearchBarBase + 各検索ウィジェット）

- [ ] 1.1 `SearchBarBase` コンポーネントの実装
  - キーワード入力欄、ヒット件数表示ラベル、次/前ジャンプ操作（ボタン＋キーバインド）を持つ共通検索バーを追加する
  - `on_search(keyword: str)`, `on_next()`, `on_prev()` コールバックと、`update_hits(current, total)` API を定義する
  - _Requirements: FR-1, NFR-1, NFR-2_

- [ ] 1.2 セッション内検索 UI の `SearchBarBase` 置き換え
  - 既存のセッション内検索ウィジェットを `SearchBarBase` ベースに書き換え、キーバインドと件数表示ロジックを共通化する
  - ChatView 側に検索結果ジャンプ用の API を追加／統合し、Flow 1 のシーケンスが成立することを確認する
  - _Requirements: FR-1, FR-4, NFR-1, AC-1, AC-4_

- [ ] 1.3 セッション一覧検索・添付検索 UI の統一
  - セッション一覧検索・添付検索についても `SearchBarBase` を利用し、Ctrl+F などの操作パターンとハイライト表現を揃える
  - 各検索結果から対象セッション／添付の位置にジャンプする処理を整理し、件数表示と連携させる
  - _Requirements: FR-1, NFR-1, AC-1, AC-5_

2. ショートカット整理とヘルプダイアログ

- [ ] 2.1 `ShortcutRegistry` の導入
  - `ShortcutMeta` 構造（key, description, category, scope）と `ShortcutRegistry` を実装し、ショートカット登録を一元化する
  - 重複キー登録時のポリシー（警告ログ + どちらを優先するか）を決め、実装に反映する
  - _Requirements: FR-2, NFR-2, NFR-3_

- [ ] 2.2 既存ショートカットの Registry 統合
  - 送信／改行／検索／レイアウト切り替えなど、MainWindow・各ウィジェットに散在するショートカット定義を `ShortcutRegistry` に登録する形にリファクタリングする
  - グローバルホットキー (`global_hotkey.py`) も説明文レベルでは Registry に統合し、表示対象として扱う
  - _Requirements: FR-2, NFR-1, NFR-2_

- [ ] 2.3 `ShortcutHelpDialog` の実装と起動導線
  - `ShortcutRegistry.get_all()` を使ってショートカット一覧をカテゴリごとに表示する `ShortcutHelpDialog` を実装する
  - F1 等のヘルプショートカット／メニューからダイアログを起動し、内容が実際の挙動と一致していることを確認する
  - _Requirements: FR-2, NFR-2, AC-2_

3. テンプレート／役割／添付導線の最適化（MessageComposer 中心）

- [ ] 3.1 `MessageComposer` 内のボタン配置と導線整理
  - テンプレート挿入・役割選択・添付要約/質問ボタンを入力欄周辺に集約し、現行 UI からの配置ずれを解消する
  - それぞれのクリックから既存ダイアログ／処理に到達するまでのステップ数を見直し、不要な中継ボタンやメニューを削減する
  - _Requirements: FR-3, NFR-1, NFR-3_

- [ ] 3.2 メインフローからのステップ数計測と微調整
  - 「チャットしながらテンプレ挿入／役割変更／添付要約」を行う代表ケースを定義し、現状と v1.7 後のステップ数・視線移動を比較する
  - 必要に応じてボタンのラベル／アイコン／ショートカットを調整し、「前より分かりやすい／早い」と言える状態まで詰める
  - _Requirements: FR-3, NFR-1, AC-3_

4. Enter/Shift+Enter・フォーカス・スクロール挙動統一

- [ ] 4.1 送信挙動設定と `MessageComposer` への集約
  - `send_behavior` 設定（`enter_to_send` / `ctrl_enter_to_send` 等）がある場合はそれを確認し、なければ導入を検討する
  - Enter / Shift+Enter の判定を `MessageComposer` に集約し、他のウィジェット側の重複ロジックを削除する
  - _Requirements: FR-4, NFR-2, NFR-3_

- [ ] 4.2 送信後のフォーカス復帰ポリシー実装
  - メッセージ送信後に必ず入力欄にフォーカスを戻す処理を `MessageComposer` に実装し、例外ケース（ダイアログオープン時など）の扱いを決める
  - 既存の「フォーカスが別のウィジェットに残る」不自然な挙動があれば洗い出し、同時に修正する
  - _Requirements: FR-4, NFR-1, AC-4_

- [ ] 4.3 ChatView / SessionView のスクロール API 実装
  - 検索結果ジャンプと新規メッセージ追加時のスクロール挙動を一元化する API（`jump_to_message` / `scroll_to_bottom_if_needed` 等）を実装する
  - 「ユーザーが手動でスクロールした場合は自動スクロールしない」といったポリシーをテスト付きで確認する
  - _Requirements: FR-1, FR-4, NFR-1, AC-1, AC-4_

5. テスト・ドキュメント・リグレッション確認

- [ ] 5.1 単体テストの追加
  - `SearchBarBase` のキーバインドと `update_hits` 表示ロジックのユニットテストを追加する
  - `ShortcutRegistry` の登録／重複検知／一覧取得テスト、および `MessageComposer` の Enter/Shift+Enter 挙動・送信後フォーカス復帰のテストを追加する
  - _Requirements: FR-1, FR-2, FR-4, NFR-2, NFR-3, AC-2, AC-4_

- [ ] 5.2 統合／UI テストと回帰テスト
  - セッション内／一覧／添付検索で同じ操作パターンが成立すること、ShortcutHelpDialog に全主要ショートカットが表示されることを UI テスト／手動テストで確認する
  - v1.6 までの主要機能（チャット、マルチセッション、検索、テンプレート／役割、添付、ホットキー）が退行していないことを、既存テスト＋追加シナリオで検証する
  - _Requirements: AC-1, AC-2, AC-3, AC-5_

- [ ] 5.3 ドキュメント／ヘルプ更新
  - ショートカット一覧（ヘルプテキスト）やユーザー向けガイドに、統一された検索操作・ショートカット・導線ルールを反映する
  - 変更された挙動（送信キー、スクロールポリシーなど）について、リリースノート等で簡潔に説明する
  - _Requirements: NFR-2, NFR-3, AC-2, AC-3_


