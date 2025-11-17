---
title: Tech Steering
description: 技術スタック・設計判断・運用方針をパターンとして保存する
updated_at: 2025-11-17
---

# 技術指針（Patterns）

## スタック（Stack）

- 言語: Python 3.11+
- GUI: PySide6（Qt6）
- HTTP クライアント: requests（同期、SSE/JSON Lines ストリーム処理）
- パッケージング: PyInstaller（単一 exe 配布）
- スタイル: PEP8、型ヒント積極利用
- 環境管理: uv + .venv（再現性あるセットアップ）

## 主要な設計判断（Key Decisions）

- 同期 HTTP を基本。OpenAI 互換 SSE / Ollama JSON Lines のストリーミングに対応し、非対応時は一括応答へフォールバック。
- UI の反応性は必要に応じてスレッド化や逐次反映で確保する。
- LLM クライアントはインターフェース（`LlmClient`）＋実装（OpenAI 互換/Ollama）で抽象化。
- 設定はユーザープロファイル配下のファイルへ保存し、既定値で初期化可能に。
- 依存は最小限を維持し、クライアント側にサーバフレームワークは持ち込まない。

## UI コンポジションとレイアウト（UI Composition & Layout）

- メインウィンドウは `MainLayoutContainer` でサイドバーとチャットペインを分割し、Qt の `QSplitter` によるリサイズを前提とする。
- レイアウトモードは `LayoutMode`（列挙）と `LayoutModeState`（Config 連動）の組み合わせで管理し、設定ファイルから現在モードを復元する。
- テーマは `ThemeTokens`（色・タイポグラフィ・余白のトークン）と CSS ビルダ関数（例: `build_main_container_styles`, `build_composer_styles`）で一元管理する。
- チャットコンポーザやサイドバーなどの UI 部品は「ロジックを薄く、スタイルはテーマへ集約」を基本とする。

## グローバルホットキー（Global Hotkey）

- Windows のグローバルホットキーは `GlobalHotkeyManager` が責務を持つ。
  - Qt の `QAbstractNativeEventFilter` を使い、`WM_HOTKEY` をフックする。
  - 実装は `ctypes` で `user32.dll` の `RegisterHotKey`/`UnregisterHotKey` を直接呼び出すシンプルなバックエンド。
- OS 依存性:
  - `sys.platform.startswith("win")` の場合のみ Win32 バックエンドを有効化し、それ以外の OS ではホットキー機能自体を無効化して安全にフォールバック。
  - バックエンド初期化や登録に失敗してもアプリ全体は継続し、ホットキー機能のみを無効にする。
- ホットキー設定は文字列表現（例: `"Ctrl+Alt+Space"`）をパーサ `parse_hotkey` で解析し、修飾キーと仮想キーコードへ変換する。

## 観測性・診断（Observability & Diagnostics）

- アプリ全体のログは `app_logger` を通じて出力し、イベント名＋ JSON メタ情報を基本とする。
  - センシティブなキー（`prompt`, `content`, `api_key`, `token` など）は自動的に `[filtered]` にマスクされる。
  - ログレベルは `info` / `warning` / `error` を使用し、`debug` は原則使わない（軽量クライアント方針）。
- ログファイル:
  - 既定の出力先は `%APPDATA%/win-llm-chat-pyside/logs/app.log`。サイズとローテーションは設定値で制御する。
  - 詳細は `docs/LOGGING_POLICY.md` を参照し、コードは方針に従う。
- 診断情報:
  - `DiagnosticsInfoProvider` がアプリバージョン・Python・OS・アクティブプロファイルなどを収集し、サポート提出用のテキストへ整形する。
  - `diagnostics_show_env_details` 設定が有効な場合のみ、データディレクトリやログディレクトリのパスを含める。

## エラーハンドリング（Error Policy）

- ネットワーク/認証/フォーマットエラーを分類し、ユーザーに意味あるメッセージを提示。
- 例外は GUI へ伝播させず、アプリ継続を優先。ログ化は簡潔に。

## ストリーミング方針（Streaming Policy）

- 文字コードは UTF-8 を明示指定。サーバ誤報告時も `errors="replace"` 等で継続。
- 形式不正フレームはスキップし、全体停止は避ける。終端は `[DONE]`（SSE）/ `done: true`（JSON Lines）。
- タイムアウトは接続/全体の双方を設定で制御。失敗時は非ストリーミングへフォールバック。
- 詳細仕様・エラー分類は `api-standards.md` を参照。

## 設定と秘密情報（Configuration & Secrets）

- ベース URL・モデル名・API キー等はハードコード禁止。設定ファイル/環境変数/定数へ分離。
- API キーはユーザープロファイル配下に保存。暗号化は将来拡張余地を確保。

## 配布・運用（Packaging & Ops）

- PyInstaller による GUI モードビルドを標準とし、起動時間/メモリ使用量を定点観測。
- Windows 10/11 での動作を優先検証。

## テスト方針（Testing Policy）

- 最低限、HTTP リクエスト組み立て/レスポンスパースのユニットテストを実施。
- GUI はスモークレベルの手動確認を基本とし、ロジックのユニット化で自動化対象を増やす。
