# ログ方針（v1.6）

アプリケーション全体でのログ出力のルールと方針を定義する。

## 基本方針

- **目的:** トラブルシューティングに必要な情報を記録しつつ、プライバシーとセキュリティを保護する
- **出力先:** `%APPDATA%/win-llm-chat-pyside/logs/app.log`（ローテーションあり）
- **形式:** テキストログ（イベント名 + JSON メタ情報）

## ログに出すもの

### 1. イベント情報
- セッション操作（作成・削除・名前変更）
- テンプレート・役割プロファイル操作（作成・編集・削除）
- ファイル添付操作（追加・削除・抽出成功/失敗）
- 設定変更（プロファイル切り替え、UI設定変更など）
- グローバルホットキー登録・解除

### 2. エラー情報
- ネットワークエラー（接続失敗、タイムアウト）
- ファイル I/O エラー（読み込み失敗、書き込み失敗）
- JSON パースエラー
- その他の例外（スタックトレースは簡略化）

### 3. システム情報
- 起動・終了
- 設定ファイルの読み込み・保存
- ディレクトリ作成
- ログファイルのローテーション

### 4. メタ情報（安全な範囲）
- ファイルパス（フルパス可）
- モデル名
- API URL（ドメイン部分のみ、クエリパラメータは除外）
- セッション ID、テンプレート ID、役割プロファイル ID
- ファイルサイズ、ページ数、テキスト長
- エラーメッセージ（ユーザー向けメッセージ）

## ログに出さないもの

### 1. センシティブ情報（自動フィルタリング）
以下のキー名を持つメタ情報は、自動的に `[filtered]` に置換される：

- `prompt`, `prompts`
- `content`, `contents`
- `body`
- `payload`
- `api_key`, `apikey`
- `authorization`, `auth`
- `token`
- `messages`

また、キー名に `prompt`, `content`, `api`, `token` が含まれる場合も同様にフィルタリングされる。

### 2. 長い文字列
300 文字を超える文字列は、先頭 300 文字 + `…` に切り詰められる。

### 3. その他
- プロンプト本文（ユーザー入力・システムプロンプト・アシスタント応答）
- メッセージ内容（チャット履歴）
- API キー・認証トークン
- 添付ファイルの抽出テキスト全文（ファイル名・サイズ・ページ数は記録）

## ログレベル

- **INFO:** 通常の操作イベント（セッション作成、設定変更など）
- **WARNING:** 警告レベルの問題（ファイル読み込み失敗、設定値の検証エラーなど）
- **ERROR:** エラーレベルの問題（例外発生、致命的な操作失敗など）

DEBUG レベルは使用しない（軽量クライアント方針に沿う）。

## ログ出力例

### 正常系
```
2025-11-15 10:30:00 INFO session.created {"session_id": "abc123...", "name": "新規セッション"}
2025-11-15 10:31:00 INFO template.saved {"template_id": "tpl-456", "title": "要約プロンプト"}
2025-11-15 10:32:00 INFO attachment.extracted {"session_id": "abc123...", "attachment_id": "att-789", "filename": "document.pdf", "page_count": 10, "text_length": 5000}
```

### エラー系
```
2025-11-15 10:33:00 ERROR session.load_failed {"session_id": "abc123...", "error": "JSON decode error: ..."}
2025-11-15 10:34:00 WARNING attachment.extract_failed {"session_id": "abc123...", "attachment_id": "att-789", "error": "Unsupported file type"}
```

### フィルタリング例
```python
# 入力
app_logger.info("chat.message_sent", {
    "prompt": "これは機密情報です",  # → [filtered]
    "content": "応答内容",  # → [filtered]
    "model": "gemma3:4b",  # → そのまま
    "session_id": "abc123..."  # → そのまま
})

# 出力
2025-11-15 10:35:00 INFO chat.message_sent {"model": "gemma3:4b", "prompt": "[filtered]", "content": "[filtered]", "session_id": "abc123..."}
```

## ログファイル管理

- **ファイル名:** `app.log`
- **最大サイズ:** 既定 5MB（設定可能）
- **ローテーション:** サイズ上限に達したら `app.log.1`, `app.log.2` などにローテーション
- **保持数:** 既定 5 ファイル（設定可能）
- **エンコーディング:** UTF-8

## 設定

ログの有効/無効・レベル・ファイルサイズ・保持数は、`config.json` の以下のフィールドで制御できる：

- `logging_enabled`: ログ出力の ON/OFF（既定: `true`）
- `logging_level`: ログレベル（`info`, `warning`, `error`、既定: `info`）
- `logging_dir`: ログディレクトリ（未設定時は既定値）
- `logging_max_file_size_mb`: 最大ファイルサイズ（MB、既定: 5）
- `logging_rotation_keep_files`: 保持ファイル数（既定: 5）

## トラブルシューティング時のログ提供

ユーザーから「ログをちょうだい」と言われた場合、以下のファイルを提供する：

1. `%APPDATA%/win-llm-chat-pyside/logs/app.log`（最新）
2. 必要に応じて `app.log.1`, `app.log.2` など（過去のログ）

**注意:** ログファイルにはセンシティブ情報は含まれないが、ファイルパスやセッション ID などが含まれる可能性がある。必要に応じて、特定のセッション ID やファイルパスをマスクして提供する。

---

最終更新: 2025-11-15 (v1.6)

