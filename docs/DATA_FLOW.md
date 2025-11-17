# データフローとストレージ構造

v2.0 時点でのデータ保存場所・フォーマット・ライフサイクルを説明する。

## 保存場所の概要

全てのデータは Windows の `%APPDATA%/win-llm-chat-pyside/` 配下に保存される。

```
%APPDATA%/win-llm-chat-pyside/
├── config.json              # アプリ設定（プロファイル、UI設定、ネットワーク設定など）
├── sessions/                # マルチセッション関連
│   ├── index.json           # セッション一覧メタ情報
│   └── session_<id>.json    # 各セッションの本体（メッセージ、添付メタ、テキスト）
├── prompt_assets/           # プロンプトテンプレート・役割プロファイル
│   ├── templates.json       # プロンプトテンプレート一覧
│   └── role_profiles.json   # 役割プロファイル一覧
└── logs/                    # ログファイル
    └── app.log              # アプリケーションログ（ローテーションあり）
```

## 各データの詳細

### 1. 設定（config.json）

**パス:** `%APPDATA%/win-llm-chat-pyside/config.json`

**フォーマット:** JSON（`Config` dataclass の `asdict()` 出力）

**主要フィールド:**
- `profiles`: 接続先プロファイルのリスト
- `current_profile_name`: 現在選択中のプロファイル名
- `history_enabled`: 履歴永続化の ON/OFF
- `history_path`: カスタム履歴パス（未設定時は既定値）
- `logging_*`: ログ設定
- `ui_*`: UI 設定（フォント、ショートカットなど）
- `global_hotkey_*`: グローバルホットキー設定

**ライフサイクル:**
- 作成: 初回起動時、デフォルト値で作成
- 更新: 設定画面での変更時に原子的に保存（`.tmp` → `config.json` 置換）
- 削除: アプリ削除時に手動削除が必要（ユーザー操作）

**バージョン:** v1.6 以降、`version` フィールドを追加（未設定時は `"1.0"` とみなす）

**マイグレーション:** v0.5 以前の単一 `base_url`/`model` 設定は、初回読み込み時に `profiles[0]` へ自動移行

---

### 2. セッション一覧（sessions/index.json）

**パス:** `%APPDATA%/win-llm-chat-pyside/sessions/index.json`

**フォーマット:** JSON 配列（`SessionMeta` のリスト）

**構造:**
```json
[
  {
    "id": "abc123...",
    "name": "セッション名",
    "created_at": "2025-11-15T10:30:00+00:00",
    "updated_at": "2025-11-15T11:00:00+00:00"
  }
]
```

**ライフサイクル:**
- 作成: 初回セッション作成時
- 更新: セッション名変更・メッセージ追加時に `updated_at` を更新
- 削除: セッション削除時に該当エントリを削除

**バージョン:** v1.6 以降、ルートに `version` フィールドを追加（未設定時は `"1.0"` とみなす）

**注意:** このファイルは「メタ情報のみ」を保持し、メッセージ本文は含まない。起動時のメモリ使用を抑えるため。

---

### 3. セッション本体（sessions/session_<id>.json）

**パス:** `%APPDATA%/win-llm-chat-pyside/sessions/session_<id>.json`

**フォーマット:** JSON（`Session` dataclass の `to_dict()` 出力）

**構造:**
```json
{
  "id": "abc123...",
  "name": "セッション名",
  "created_at": "2025-11-15T10:30:00+00:00",
  "updated_at": "2025-11-15T11:00:00+00:00",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "role_profile_id": "profile-id-123" | null,
  "attachments": [
    {
      "id": "att-123",
      "session_id": "abc123...",
      "filename": "document.pdf",
      "size_bytes": 102400,
      "mime_type": "application/pdf",
      "page_count": 10,
      "text_length": 5000,
      "status": "ready",
      "error_message": null,
      "length_warning": false
    }
  ],
  "attachment_texts": {
    "att-123": "抽出されたテキスト全文..."
  }
}
```

**ライフサイクル:**
- 作成: セッション作成時、または v1.0 からの移行時
- 更新: メッセージ追加・添付追加・役割プロファイル変更時に原子的に保存
- 削除: セッション削除時にファイル自体を削除

**バージョン:** v1.6 以降、`version` フィールドを追加（未設定時は `"1.0"` とみなす）

**注意:** 
- `attachment_texts` はセッション JSON 内に保存される（別ファイル化しない）。軽量性重視のため。
- 添付ファイルの元ファイル（PDF など）は保存しない。テキスト抽出結果のみを保持。

---

### 4. プロンプトテンプレート（prompt_assets/templates.json）

**パス:** `%APPDATA%/win-llm-chat-pyside/prompt_assets/templates.json`

**フォーマット:** JSON（`{"templates": [...]}` 形式）

**構造:**
```json
{
  "version": "1.0",
  "templates": [
    {
      "id": "tpl-123",
      "title": "テンプレート名",
      "body": "Markdown形式の本文...",
      "created_at": "2025-11-15T10:30:00+00:00",
      "updated_at": "2025-11-15T10:30:00+00:00"
    }
  ]
}
```

**ライフサイクル:**
- 作成: テンプレート作成時
- 更新: テンプレート編集時
- 削除: テンプレート削除時（配列から要素を削除）

**バージョン:** v1.6 以降、ルートに `version` フィールドを追加

---

### 5. 役割プロファイル（prompt_assets/role_profiles.json）

**パス:** `%APPDATA%/win-llm-chat-pyside/prompt_assets/role_profiles.json`

**フォーマット:** JSON（`{"profiles": [...]}` 形式）

**構造:**
```json
{
  "version": "1.0",
  "profiles": [
    {
      "id": "role-123",
      "name": "役割名",
      "system_prompt": "Markdown形式のsystem prompt...",
      "created_at": "2025-11-15T10:30:00+00:00",
      "updated_at": "2025-11-15T10:30:00+00:00",
      "is_default": false
    }
  ]
}
```

**ライフサイクル:**
- 作成: 役割プロファイル作成時
- 更新: 役割プロファイル編集時
- 削除: 役割プロファイル削除時（配列から要素を削除）

**バージョン:** v1.6 以降、ルートに `version` フィールドを追加

---

### 6. ログ（logs/app.log）

**パス:** `%APPDATA%/win-llm-chat-pyside/logs/app.log`

**フォーマット:** テキストログ（RotatingFileHandler によるローテーション）

**出力内容:**
- イベント名とメタ情報（JSON 形式）
- センシティブ情報（プロンプト本文、API キー、メッセージ内容など）は `[filtered]` に置換

**ライフサイクル:**
- 作成: 初回ログ出力時
- 更新: アプリ実行中に追記
- ローテーション: ファイルサイズ上限（既定 5MB）に達したら `app.log.1`, `app.log.2` などにローテーション
- 削除: 古いログファイルは保持数上限（既定 5 ファイル）を超えた分が自動削除

**ログ方針（v1.6 時点）:**
- **ログに出すもの:** イベント名、エラーメッセージ、ファイルパス、モデル名、設定変更、セッション操作
- **ログに出さないもの:** プロンプト本文、メッセージ内容、API キー、認証トークン
- **長い文字列:** 300 文字を超える場合は切り詰めて `…` を付与

---

## データフロー図

```
起動時:
  config.json → Config オブジェクト
  sessions/index.json → SessionMeta リスト（メタのみ）
  sessions/session_<id>.json → Session オブジェクト（選択時のみロード）

セッション操作時:
  メッセージ追加 → Session.messages 更新 → session_<id>.json 原子的保存
  セッション名変更 → Session.name 更新 → session_<id>.json + index.json 原子的保存

テンプレート・役割操作時:
  作成/編集/削除 → prompt_assets/*.json 原子的保存

設定変更時:
  設定画面での変更 → config.json 原子的保存
```

---

## バージョン管理とマイグレーション

### バージョンフィールド

v1.6 以降、各 JSON ファイルに `version` フィールドを追加する。

- **未設定時:** `"1.0"` とみなす（後方互換）
- **設定時:** `"1.6"`, `"2.0"` などの文字列

### マイグレーションポリシー

1. **読み込み時に自動マイグレート**
   - 旧バージョンのファイルを読み込んだ際、最新フォーマットへ変換して保存し直す
   - ユーザー操作は不要

2. **破壊的変更の扱い**
   - フィールド追加: デフォルト値で補完
   - フィールド削除: 読み込み時に無視（後方互換）
   - フィールド名変更: 旧名を読み込んで新名で保存（移行）

3. **既存データの保護**
   - v1.0〜v1.5 のデータは、v1.6 以降でも読み込めることを保証
   - マイグレーション失敗時は、元ファイルを保持したままエラーを返す

---

## リポジトリ層の責務

以下のリポジトリクラスが、UI 層からの直接ファイル I/O を防ぐ境界を提供する。

- `SessionRepository`: セッションの読み書き
- `TemplateRepository`: プロンプトテンプレートの読み書き
- `RoleProfileRepository`: 役割プロファイルの読み書き
- `ProfileRepository` (via `config.py`): 設定の読み書き

**原則:** UI 層（`ui_main.py` など）からは、これらのリポジトリを経由してのみデータにアクセスする。直接 `open()` や `json.load()` を呼ばない。

---

## トラブルシューティング

### よくある問題

1. **JSON ファイルが破損している**
   - 症状: 起動時にエラー、セッションが読み込めない
   - 対処: `.bak` ファイルがあれば復元を試みる。なければ手動で JSON を修正

2. **ディレクトリが存在しない**
   - 症状: 初回起動時、またはデータディレクトリが削除された場合
   - 対処: 自動的にディレクトリを作成する（`mkdir(parents=True, exist_ok=True)`）

3. **権限エラー**
   - 症状: `%APPDATA%` への書き込みが拒否される
   - 対処: Windows のユーザー権限を確認。必要に応じて管理者権限で実行

4. **ファイルロック**
   - 症状: 複数インスタンス起動時、またはファイルが他のプロセスで開かれている
   - 対処: 原子的保存（`.tmp` → 置換）により、通常は問題にならない。それでも発生する場合は、アプリを再起動

---

最終更新: 2025-11-15 (v1.6)

