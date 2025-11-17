# Tasks

## Overview

v1.6「メイン UI 二段モード（集中／コンパクト）」の requirements/design に基づき、  
レイアウトモード状態管理、メインレイアウト再構成、メッセージコンポーザ統合、  
テーマトークン基盤、テスト・視覚検証を段階的に実装するためのタスク分解。

## Task List

1. レイアウトモード状態と設定永続化

- [x] 1.1 `LayoutMode` 列挙と `MainWindow.current_layout_mode` の導入

  - `LayoutMode` 列挙型（`FOCUSED`, `COMPACT`）を定義し、`MainWindow` に現在モードを保持するフィールドとゲッター／セッターを追加する
  - 起動時のデフォルトモードを `FOCUSED` とし、内部的には列挙／文字列表現をどちらも扱えるようにする
  - _Requirements: FR-1, FR-2, FR-3_

- [x] 1.2 `config` への `layout_mode` 設定追加と後方互換
  - `config.py` の設定スキーマに `layout_mode: str` を追加し、既存設定ファイルにキーがない場合でも安全に読み込めるようにする
  - 文字列値 `"focused"` / `"compact"` 以外が来た場合はログに警告を出しつつ `"focused"` にフォールバックする
  - _Requirements: FR-3, NFR-3, AC-3_

2. メインレイアウト再構成（MainLayoutContainer）

- [x] 2.1 `MainLayoutContainer` の新設と `QSplitter` ベース 2 分割レイアウト

  - 左サイドバーとチャットパネルを内包する `MainLayoutContainer`（もしくは同等責務）を追加し、内部に `QSplitter` を持つ構造にする
  - 既存のセッションリスト／チャットビューウィジェットをコンテナに移し替え、外部 API（メソッド呼び出し）は可能な限り互換に保つ
  - _Requirements: FR-1, NFR-2, NFR-3_

- [x] 2.2 `set_layout_mode` によるサイドバー幅制御
  - `MainLayoutContainer.set_layout_mode(mode: LayoutMode)` を実装し、`FOCUSED` では推奨幅、`COMPACT` では最小幅（ほぼ非表示）になるように `QSplitter` のサイズを制御する
  - 連続トグル時にも不自然な揺れやチラつきが出ないよう、最小幅／推奨幅を定数として定義し、マジックナンバーを避ける
  - _Requirements: FR-1, FR-2, NFR-1, NFR-2, AC-1, AC-2_

3. メッセージコンポーザ統合（MessageComposerWidget）

- [x] 3.1 `MessageComposerWidget` の骨格実装

  - 既存の入力欄／送信ボタン／添付操作／テンプレート選択／要約・質問ボタンなどを統合する `MessageComposerWidget` を新規追加し、イベントシグナル経由で既存送信ロジックに委譲する
  - 現時点では集中モード向けのフル機能レイアウトを優先して実装し、UI 配置の責務を `ui_main.py` から切り離す
  - _Requirements: FR-1, NFR-3_

- [x] 3.2 コンパクトモード向け UI の分岐と内部 `set_layout_mode`

  - `MessageComposerWidget.set_layout_mode(mode: LayoutMode)` を実装し、`COMPACT` の場合は 1 行入力＋アイコンボタン列に UI を縮約し、添付一覧はポップオーバー／ダイアログ表示に切り替える
  - 機能自体は削らず、アクセスパスのみ変わるようにする（添付・テンプレ・要約／質問操作がすべて利用可能であることを確認）
  - _Requirements: FR-2, NFR-1, NFR-3, AC-2, AC-5_

- [x] 3.3 既存メインウィンドウへのコンポーザ統合
  - `ui_main.py`（および必要なら `session_widgets.py`）から既存の入力欄／ボタン群を取り外し、代わりに `MessageComposerWidget` を下部に配置する
  - 既存のテスト（送信フロー／添付フロー）を壊さないよう、信号／メソッド名・引数の互換性を維持する
  - _Requirements: FR-1, FR-2, AC-5_

4. レイアウトモード切り替え UI とショートカット

- [x] 4.1 メニュー／アクションとしてのモードトグル追加

  - メニューバーまたは設定メニューに「集中モード／コンパクトモード」トグルアクションを追加し、現在のモードが視覚的に分かるようチェック状態／ラベルを制御する
  - トグル時に `MainWindow.current_layout_mode` を更新し、`MainLayoutContainer` と `MessageComposerWidget` 双方に `set_layout_mode` を通知する
  - _Requirements: FR-3, NFR-1_

- [x] 4.2 キーボードショートカット（例: Ctrl+Shift+M）の実装

  - メインウィンドウフォーカス中のみ有効なショートカットとしてモードトグルを登録し、`GlobalHotkey` 実装と競合しないようにスコープを限定する
  - ショートカット連続押下時でもレイアウトが破綻しないことを確認し、必要ならトグル操作をデバウンスする
  - _Requirements: FR-3, NFR-2, AC-3_

- [x] 4.3 モード状態の保存と復元
  - トグル操作のたびに `config.layout_mode` を更新し、アプリ終了時に最後のモードが確実に保存されるようにする
  - 起動時に `config.layout_mode` を読み取り、`MainWindow` 初期化時に `current_layout_mode` とレイアウトに反映する
  - _Requirements: FR-3, AC-3_

5. テーマトークン基盤と Themed UI の導入

- [x] 5.1 `theme.py`（もしくは `theme_tokens.py`）にトークンと ThemeRole を定義

  - カラー／タイポグラフィ／スペーシングのトークンと、`ChatBubbleUser` / `ChatBubbleAssistant` / `Sidebar` / `Composer` などの ThemeRole を定義する
  - 値は現状のダークテーマに合わせつつ、palette() 参照を優先し、直接色はアプリ固有の差別化に必要な最小限に留める
  - _Requirements: FR-4, NFR-1, NFR-3, AC-4_

- [x] 5.2 `MessageComposerWidget` / メインレイアウトへのトークン適用

  - `MessageComposerWidget` とチャットパネルに対して、トークン値から構築した QSS を適用し、色・フォント・余白のハードコードを排除する
  - 集中／コンパクト両モードで読みやすさと一貫性が保たれているか、行間やパディングを調整する
  - _Requirements: FR-1, FR-2, FR-4, NFR-1, AC-1, AC-2, AC-4_

- [x] 5.3 既存チャットビューの最低限のテーマ統合
  - チャットログの気泡（User / Assistant）の背景色・文字色・余白をトークン化し、既存 QSS から直接色を削減する
  - 24 インチ半画面で長文が読みやすいことを視覚的に確認し、必要に応じてフォントサイズ／行間を微調整する
  - _Requirements: NFR-1, AC-1, AC-4_

6. テスト・視覚検証・リグレッション確認

- [x] 6.1 レイアウトモード関連ロジックのユニットテスト

  - `LayoutMode` トグル、`MainLayoutContainer.set_layout_mode` のサイドバー幅制御、`MessageComposerWidget.set_layout_mode` の表示制御について単体テストを追加する
  - 無効値／未知モード／設定破損時のフォールバック挙動をテストし、例外を出さずに安全に復元できることを確認する
  - _Requirements: FR-1, FR-2, FR-3, NFR-2, NFR-3, AC-3_

- [x] 6.2 UI / E2E / 手動テストシナリオ
  - 集中モードで 24 インチ半画面にウィンドウを配置し、長文の読み書きが快適に行えること（スクロール・入力レスポンス含む）を確認する
  - コンパクトモードで「起動 → 1〜2 往復の Q&A → ウィンドウクローズ」のフローがスムーズに行えること、モード切り替えやサイドバー非表示で既存機能が退行していないことを確認する
  - 新旧テーマ／モードを跨いで、追加 UI に色・フォント・余白のハードコーディングが残っていないことを確認する（コードレビューを含む）
  - _Requirements: AC-1, AC-2, AC-3, AC-4, AC-5_
