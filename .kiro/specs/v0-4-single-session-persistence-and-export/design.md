# Design Document

## 概要
v0.4「単一セッション永続化とエクスポート」を段階導入する。初期は既存構造を拡張し（Option C の初手）、安全なファイルI/OとUI連携を最小変更で実現。複雑化の兆候が出たら責務分割（HistoryService/Exporter）へ移行可能な形にする。

## スコープ/非スコープ
- スコープ
  - 終了時の自動保存／起動時の自動ロード
  - 明示的なMarkdownエクスポート
  - 履歴サイズのソフト上限と非ブロッキング警告
  - 安全な原子的保存・簡易バックアップ、UIフリーズ回避
- 非スコープ
  - 複数セッション管理、検索、圧縮、暗号化、RAG 等

## アーキテクチャ
```text
UI(MainWindow)
 ├── メニュー（ファイル→Markdownで保存…）
 ├── 起動時ロード/終了時保存のフック
 └── Worker（必要に応じてI/Oを委譲）
Infra
 ├── storage.py（原子的保存・バックアップ・Markdown生成）
 └── config.py（history/export 設定値の追加）
```

## 主要変更点（ファイル別）
- src/win_llm_chat_pyside/storage.py
  - save_session_atomic(messages, path): 一時ファイルへ書込→os.replace() で原子的置換。`.bak` を1世代保持可
  - load_session_safe(path): JSON読み込み（例外→呼出側で通知）。未知フィールドは無視
  - render_markdown(messages, metadata) -> str: ユーザー/アシスタント区別とメタ情報ヘッダを付与
  - export_markdown_file(messages, path, metadata): 上記テキストを書き出し
- src/win_llm_chat_pyside/ui_main.py
  - 起動時: 設定と保存先から `load_session_safe` を試行。失敗は新規開始＋情報ダイアログ
  - 終了時: `closeEvent` で `save_session_atomic` 実行（必要なら Worker）。エラーは非致命で通知
  - メニュー: 「ファイル」→「この会話をMarkdownで保存…」を追加（QFileDialog）
  - 上限警告: 送信前/保存前に message 数・文字数を評価し、非ブロッキング通知
- src/win_llm_chat_pyside/config.py（既定値つきで後方互換）
  - history_enabled: bool = True
  - history_format: Literal['json','markdown'] = 'json'
  - history_path: Optional[str] = None  # 既定は %APPDATA%/win-llm-chat-pyside/history/session.json
  - history_max_messages: int = 400
  - history_max_chars: int = 200000
  - export_default_dir: Optional[str] = None
  - export_filename_pattern: str = "Chat-{yyyy-MM-dd HH-mm}.md"

## データモデル/フォーマット
- ランタイム `Message` は変更しない（後方互換重視）
- JSON保存はトップレベルにメタと `messages` を格納。各要素は `{role, content, ts}` を推奨（`ts` は保存専用で、ロード時は無視可）

## スレッド/非ブロッキングI/O
- 小規模I/Oは同期でも可だが、ファイルサイズ増に備え Worker（QThread）を用意
- UI は待機インジケータを出さず、失敗時のみ簡潔通知

## ストレージ安全性
- 同一ディレクトリに temp 書込→`os.replace()` で原子的置換
- 直前の `.bak` を保持し、ロード失敗時に復旧提案

## エラーハンドリング
- ロード失敗: 新規セッションで継続＋情報ダイアログ
- 保存失敗: 非致命のエラーダイアログ＋次回案内。ログに原因を簡潔出力
- 機密混入回避: APIキー等は保存対象外。将来の検査フック余地を残す

## UIワイヤリング
- メニュー新設: menubar.addMenu("ファイル") → action「この会話をMarkdownで保存…」
- export: `QFileDialog.getSaveFileName` でパス取得→`export_markdown_file`
- 既存の Markdown 表示（QTextBrowser）は流用

## テスト戦略
- storage: 原子的保存の単体テスト、破損/不正JSON時の挙動、バックアップ復旧
- ui_main: 起動時ロード・終了時保存フックのスモーク、エクスポートのダイアログ分岐
- 上限警告: 境界値テスト（messages/chars）

## 段階的切り出し（将来）
- `history_service.py` と `exporter.py` を新設し、UI からの直接呼び出しを移譲
- 大規模化時に責務分離・テスト容易性を強化

## Open Questions
- 上限警告のUI様式（ステータスバー vs 非モーダルダイアログ）の最適化
- 既定保存先の正確なパス（ポータブル版配布時の扱い）
- Markdown ヘッダに含めるメタ情報の粒度（モデル/プロファイル/開始時刻など）


