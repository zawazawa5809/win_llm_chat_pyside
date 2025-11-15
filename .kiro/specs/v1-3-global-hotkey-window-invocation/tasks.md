# Tasks

## Overview

v1.3「グローバルホットキー & ウィンドウ呼び出し」の requirements/design に基づき、GlobalHotkeyManager・WindowController・設定統合・ログ／テストを段階的に導入するための実装タスク分解。

## Task List

1. インフラ層: GlobalHotkeyManager の導入

- [x] 1.1 OS 依存ホットキー API ラッパーの設計とスタブ実装
  - Windows 環境向けに、グローバルホットキー登録／解除を行う `GlobalHotkeyManager` インターフェースと最小スタブ実装を追加
  - ライブラリ採用有無（外部ライブラリ or 自前 ctypes/win32api）を決め、将来の差し替えがしやすい抽象にする
  - _Requirements: FR-1, FR-3, NFR-1, NFR-2_
- [x] 1.2 ホットキー登録・解除・設定反映の実装
  - `register(hotkey: str, callback: Callable[[], None]) -> bool` と `unregister() -> None`、`apply_settings(enabled: bool, hotkey: Optional[str], callback)` を実装
  - 登録失敗時は False を返すか例外をラップし、呼び出し側で UI 表示とフォールバックができるようにする
  - _Requirements: FR-1, FR-3, FR-4, NFR-1, NFR-4_

2. UI 層: WindowController の導入とウィンドウトグル

- [x] 2.1 WindowController クラスとトグルロジック実装
  - `QMainWindow` をラップ or 委譲する `WindowController`（もしくは同等の責務を持つクラス）を追加し、`toggle_visibility()` / `show_and_focus()` / `minimize_or_hide()` を実装
  - 現在のウィンドウ状態（表示／最小化・フォーカス）と「常に最前面」設定を考慮して、直感的なトグル挙動を定義
  - _Requirements: FR-1, FR-5, FR-6, NFR-2, NFR-3_
- [x] 2.2 GlobalHotkeyManager と WindowController の配線
  - ホットキーコールバックとして `WindowController.toggle_visibility()` を渡すように `app.py` / `ui_main.py` を拡張
  - 既存の「常に最前面」設定と干渉しないよう、トグル時のウィンドウフラグ操作を確認・調整
  - _Requirements: FR-1, FR-5, FR-6, NFR-1, NFR-2_

3. 設定統合: Config / SettingsDialog

- [x] 3.1 設定スキーマ拡張
  - `config.py` に `hotkey_enabled: bool` と `hotkey_combination: str`（例: `"Ctrl+Alt+Space"`）を追加し、既存設定ファイルとの後方互換性を確保
  - デフォルト値を ROADMAP の方針に沿った衝突しにくいキーに設定
  - _Requirements: FR-2, FR-3, NFR-3_
- [x] 3.2 SettingsDialog への UI 追加
  - グローバルホットキーの現在値表示と編集 UI（テキスト入力 or 専用キーバインドキャプチャ）を追加
  - 有効／無効のチェックボックスと説明文（他アプリと競合する可能性があること）を表示
  - _Requirements: FR-2, NFR-3_
- [x] 3.3 設定変更時のホットキー再登録
  - 設定保存時に `GlobalHotkeyManager.apply_settings(...)` を呼び、再起動なしで新しい設定が反映されるようにする
  - 無効化された場合は登録解除し、以降のホットキー押下では何も起こらないことを保証
  - _Requirements: FR-2, FR-3, NFR-1, NFR-2_

4. エラー処理・ログ・安定化

- [x] 4.1 ホットキー競合時のユーザー通知
  - 競合や OS エラーで登録に失敗した場合、設定画面またはダイアログで「他アプリと競合している可能性」を示すメッセージを表示
  - 失敗時はホットキー機能のみ無効化し、チャット機能はそのまま利用できるようにする
  - _Requirements: FR-4, NFR-1, NFR-3, NFR-4_
- [x] 4.2 ログ出力とトラブルシューティング
  - 登録／解除の成否、設定値との不整合、OS 例外内容などをアプリのログに出力（ただしキー入力の生データは記録しない）
  - 仮想デスクトップやリモートデスクトップでの制限事項をログ or ドキュメントに残し、完璧な動作を保証しないことを明示
  - _Requirements: NFR-1, NFR-4_

5. テストと検証

- [x] 5.1 GlobalHotkeyManager の単体テスト
  - OS 呼び出し部分をモックし、登録／解除ロジックとエラー時の戻り値・例外処理を検証
  - 想定外の設定値（無効なキー文字列など）の扱いをテスト
  - _Requirements: FR-1, FR-3, FR-4, NFR-1, NFR-2, NFR-4, AC-1〜AC-4_
- [x] 5.2 WindowController の単体テスト
  - 可視状態／最小化／フォアグラウンドなどの状態遷移に対して `toggle_visibility()` が期待どおりに動くかをテスト（モックウィンドウで検証）
  - 「常に最前面」設定 ON/OFF を組み合わせた場合の動作を確認
  - _Requirements: FR-1, FR-5, FR-6, NFR-2, NFR-3, AC-1, AC-5_
- [x] 5.3 手動 UI / 実機テストシナリオ
  - バックグラウンド／最小化／前面表示の各状態からホットキーを押し、期待どおりのトグル動作になるかを確認
  - 設定変更（キー変更・無効化）後に再起動なしで反映されるかを確認
  - 他アプリとホットキーが競合するケースでのエラー表示・ログ出力・アプリ継続動作を確認
  - _Requirements: AC-1〜AC-5, NFR-1〜NFR-3_

6. 常時最前面（Always-on-top）機能の実装

- [ ] 6.1 Config に `always_on_top` フラグを追加
  - `Config` に `always_on_top: bool = False` を追加し、`_config_from_dict` で後方互換付きで復元できるようにする
  - 既存設定ファイルにキーがなくても安全に読み込めるようにする
  - _Requirements: FR-5, NFR-1, NFR-3_
- [ ] 6.2 SettingsDialog に「常に最前面」設定 UI を追加
  - 「表示・フォント」または「チャット・挙動」タブにチェックボックス（例: 「常に最前面に表示する」）を追加
  - 説明文で「グローバルホットキーと併用可能」「他アプリより前面に固定される」ことを明示する
  - `get_config()` で `cfg.always_on_top` に反映する
  - _Requirements: FR-5, NFR-3_
- [ ] 6.3 MainWindow 初期化時に最前面フラグを適用
  - `MainWindow.__init__` 内で `self.config.always_on_top` を見て `Qt.WindowStaysOnTopHint` を反映する
  - 必要に応じて再表示処理（`show()` / `showNormal()`）を行い、フラグ変更が実際のウィンドウに効くようにする
  - _Requirements: FR-5, NFR-1, NFR-2_
- [ ] 6.4 WindowController からのトグル時に最前面状態が破綻しないことを確認
  - `WindowController` のトグル挙動が、`always_on_top` の ON/OFF に関わらず自然になるように確認し、必要であれば最前面フラグ更新用のメソッドを追加
  - 常時最前面 ON の状態でホットキーで最小化/再表示を繰り返してもフラグが抜けないことを保証する
  - _Requirements: FR-1, FR-5, FR-6, AC-1, AC-5_
- [ ]\* 6.5 常時最前面 + ホットキーの手動テストシナリオ
  - 常時最前面 ON/OFF とグローバルホットキーの組み合わせで、バックグラウンド／最小化／前面表示の各状態から期待どおりに表示/最小化トグルするか確認
  - 他アプリ使用中でも「ウィンドウが消えたまま復帰しない」「フォーカス不能になる」といった重大な UX 問題が発生しないことを確認
  - _Requirements: FR-5, AC-5, NFR-1〜NFR-3_

## Milestones

- M1: GlobalHotkeyManager スタブと WindowController 導入（1.x, 2.1）
- M2: ホットキー登録／解除ロジックとウィンドウトグル配線完了（1.2, 2.2）
- M3: 設定統合と UI 反映（3.x）
- M4: エラー処理・ログ・テスト整備（4.x, 5.x）

## Out of Scope（確認）

- Windows 以外の OS 向けグローバルホットキー実装
- マクロ／スニペットツールのようなホットキー拡張機能
- 仮想デスクトップ／マルチモニタごとに異なる高度なウィンドウ配置制御
