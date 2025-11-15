# Overview

**Purpose**: 本機能は、LLM チャットクライアントに「プロンプトテンプレート」と「役割プロファイル（system prompt）」の管理機能を追加し、ユーザーが毎回長い前置きプロンプトを書くことなく、一貫した指示と役割設定を素早く適用できるようにする。
**Users**: 日常的に同種の指示を多用する一般ユーザーおよび、案件ごとに system prompt を切り替えて使いたいパワーユーザー。
**Impact**: 既存のチャット送信フロー・セッション管理フローに「テンプレート挿入」と「セッションごとの役割プロファイル適用」のフックを追加するが、メッセージ保存形式やセッション JSON 形式は可能な限り後方互換を維持する。

### Goals

- プロンプトテンプレートをローカル JSON で管理し、UI から再利用できるようにする。
- 役割プロファイルをセッション単位で選択・変更できるようにし、system メッセージとして適用する。
- 既存のセッション履歴・設定（`history_enabled` など）と矛盾しないシンプルな構造にとどめる。

### Non-Goals

- サーバ側でのテンプレート共有・同期機能は提供しない。
- RAG・添付ファイル・検索機能との連携は本バージョンのスコープ外とする。
- 役割プロファイルごとの権限管理や複雑なロールベースアクセス制御は行わない。

## Architecture

### Existing Architecture Analysis

- 設定・プロファイル系は `config.py`, `profile_repository.py` などで JSON ベースのローカル永続化を採用している。
- セッションは `models.py` の `Session`, `SessionMeta` と `session_repository.py` により、`index.json` + `session_<id>.json` で管理されている。
- UI は `ui_main.py` と `session_widgets.py` の PySide ベース構成であり、設定ダイアログ（タブ構成）とセッションリストパネルが既に存在する。
- 軽量クライアント方針により、常駐インデックス構築や複雑な DB 導入は避ける必要がある。

### Architecture Pattern & Boundary Map

**Architecture Integration**:

- Selected pattern: 既存と同様の「ローカル JSON を扱うリポジトリ層 + PySide UI」パターンを踏襲する。新たなサービス層は作らず、既存の構造に沿って小さなリポジトリと UI コンポーネントを追加する。
- Domain/feature boundaries:
  - 「テンプレート・役割プロファイルの定義と永続化」は新規のリポジトリ／モデルに閉じる。
  - 「適用タイミング（入力欄への挿入・system メッセージ挿入）」は UI / セッション管理側からリポジトリを利用して行う。
- Existing patterns preserved:
  - JSON ファイル 1〜数個で完結するローカルストレージ。
  - UI → リポジトリ → モデル のシンプルな同期フロー。
- New components rationale:
  - テンプレ／役割はセッションとは独立した再利用可能資産のため、セッション JSON に埋め込まず専用の JSON に分離する。
  - これによりセッション数とは独立してテンプレ数を管理でき、v1.4 以降の機能ともコンフリクトしにくい。
- Steering compliance:
  - 軽量・ローカル完結・JSON ベースという v2.0 ゴールの制約に従い、SQLite などは導入しない。
  - UI 変更は既存ダイアログへのタブ追加／セクション追加に留める。

### Technology Stack

| Layer                    | Choice / Version                                  | Role in Feature                               | Notes                                        |
| ------------------------ | ------------------------------------------------- | --------------------------------------------- | -------------------------------------------- |
| UI                       | PySide6                                           | テンプレ一覧・役割プロファイル選択 UI         | 既存の設定ダイアログ・セッションパネルに統合 |
| Domain/Models            | Python dataclasses                                | テンプレ／役割プロファイル定義                | `models.py` または専用モジュールに追加       |
| Data / Storage           | JSON ファイル                                     | テンプレ／役割プロファイルのローカル永続化    | 1〜2 ファイルに集約                          |
| Application              | 既存 `session_manager`, `profile_repository` など | 適用ロジック（system メッセージ／入力欄挿入） | 既存フローにフック追加                       |
| Infrastructure / Runtime | Python 3.x                                        | 特になし                                      | 追加依存は避ける                             |

## System Flows

### フロー 1: プロンプトテンプレートの作成と適用

- ユーザーが設定画面（または専用テンプレ管理ダイアログ）を開き、新規テンプレートを作成する。
- UI コンポーネントがテンプレリポジトリに対して `save_templates([...])` を呼び出し、JSON ファイルを更新する。
- チャット画面でユーザーがテンプレート選択 UI（ドロップダウンやメニュー）からテンプレートを選択する。
- クライアントは選択されたテンプレートの `body` を取得し、入力欄に挿入する（既存テキストの扱いは「追記 or 置換」で明示的に決める）。

### フロー 2: 役割プロファイルの選択とセッションへの適用

- ユーザーが役割プロファイル管理 UI から `name` と `system_prompt` を編集し、リポジトリ経由で JSON に保存する。
- 新規セッション作成ダイアログで、利用可能な役割プロファイル一覧を取得してコンボボックス表示する。
- ユーザーがプロファイルを選んでセッションを作成すると、`Session` 生成時に先頭 system メッセージとして `system_prompt` が挿入される。
- 既存セッションのプロファイル変更では、警告ダイアログを表示したうえで、以降のメッセージに対する挙動変化をユーザーが受け入れることを前提に反映する（既存メッセージ自体は変更しない）。

## Requirements Traceability

| Requirement | Summary                                | Components                                                   | Interfaces                               | Flows    |
| ----------- | -------------------------------------- | ------------------------------------------------------------ | ---------------------------------------- | -------- |
| 1.1–1.5     | プロンプトテンプレートの管理・適用     | TemplateRepository, TemplateManagerUI                        | load/save テンプレ API, テンプレ挿入操作 | フロー 1 |
| 2.1–2.5     | 役割プロファイルの管理・セッション適用 | RoleProfileRepository, SessionCreationDialog, SessionManager | プロファイル一覧取得／適用 API           | フロー 2 |

## Components and Interfaces

### Domain / Repository

#### TemplateRepository

| Field        | Detail                                                         |
| ------------ | -------------------------------------------------------------- |
| Intent       | プロンプトテンプレートの読み書きを JSON ファイル越しに提供する |
| Requirements | 1.1, 1.2, 1.4, 1.5                                             |

**Responsibilities & Constraints**

- テンプレート一覧の取得・保存を一手に引き受ける。
- JSON 構造のバージョニング（フィールド追加時の後方互換）を考慮する。
- 読み込みエラー時は安全側（空リスト扱い＋ログ出力）に倒す。

**Dependencies**

- Outbound: ファイルシステム（アプリの設定ディレクトリ）へのアクセス。
- External: 既存の設定パス解決ロジック（config/ストレージ関連）。

**Contracts**: Service [x] / State [x]

**Service Interface（イメージ）**

```python
class TemplateRepository:
    def load_templates(self) -> list[PromptTemplate]: ...
    def save_templates(self, templates: list[PromptTemplate]) -> None: ...
```

#### RoleProfileRepository

| Field        | Detail                                                    |
| ------------ | --------------------------------------------------------- |
| Intent       | 役割プロファイル（system prompt）の永続化と取得を担当する |
| Requirements | 2.1, 2.4, 2.5                                             |

**Responsibilities & Constraints**

- プロファイルの追加・更新・削除と一覧取得を提供する。
- 削除しても既存セッションの system メッセージには影響を与えない（セッション JSON に直接書き込まれたテキストはそのまま）。

**Contracts**: Service [x] / State [x]

## Data Models

### Domain Model

- `PromptTemplate`
  - Fields: `id`（文字列 UUID）, `title`（表示名）, `body`（Markdown テキスト）, `created_at`, `updated_at`。
  - Invariants: `title` は空文字禁止、`body` は非空を推奨（空の場合は警告）。
- `RoleProfile`
  - Fields: `id`, `name`, `system_prompt`, `created_at`, `updated_at`, `is_default`。
  - Invariants: 同時に複数の `is_default=True` を許可しない（UI 側で制御）。

### Logical Data Model

- テンプレート JSON 例（論理構造のみ）:
  - `templates.json`: `{ "templates": [ { "id": "...", "title": "...", "body": "...", "created_at": "...", "updated_at": "..." }, ... ] }`
- 役割プロファイル JSON 例:
  - `role_profiles.json`: `{ "profiles": [ { "id": "...", "name": "...", "system_prompt": "...", "created_at": "...", "updated_at": "...", "is_default": false }, ... ] }`

### Physical Data Model

- ストレージは既存設定と同じディレクトリ配下に 2 ファイル追加する想定（正確なパスは実装時に config と揃える）。
- ロック／同時書き込みは単一クライアント前提のため簡易な排他で十分とする（実装は後述のエラーハンドリングで考慮）。

## Error Handling

### Error Strategy

- JSON 読み込みエラーやパースエラー時は、空リストとして扱いつつログに詳細を出力する。
- 書き込みエラー時はユーザーに分かる形でエラーダイアログを表示し、「テンプレート／プロファイルが保存されていない」ことを明示する。

### Error Categories and Responses

- User Errors: 無効なタイトル（空文字など）の場合は UI レベルでバリデーションし、保存処理を行わない。
- System Errors: ディスク書き込み不可・パス解決失敗などはログ + エラーダイアログで通知し、アプリが落ちないようにする。

## Testing Strategy

- Unit Tests:
  - TemplateRepository の読み書き（正常系・壊れた JSON・空ファイル）。
  - RoleProfileRepository の追加・更新・削除とデフォルトフラグ制御。
  - ドメインモデルのバリデーション（空タイトルなど）。
- Integration Tests:
  - UI からテンプレを作成 → 再起動後に一覧へ反映されること。
  - 新規セッション作成時の役割プロファイル選択 → system メッセージへの反映。
  - 既存セッションでのプロファイル変更時の警告ダイアログ表示。
- E2E/UI Tests（手動 or 自動）:
  - テンプレ挿入後にチャット送信が正常動作すること。
  - 役割プロファイル削除後も過去セッションが読み込み・表示できること。
