# プロジェクト仕様: Windows LLM チャットクライアント (Python + PySide6)

## 0. 概要

### 0.1 プロジェクト名（仮）

`win-llm-chat-pyside`  
Windows 10/11 クライアント PC から、Ollama または社内 LLM エンドポイントへ接続する軽量チャットクライアント。

### 0.2 目的

- 8GB RAM 程度の非 GPU Windows 端末でも安定して動作する、**軽量なチャット用 GUI クライアント**を提供する。
- LLM 本体はサーバ側（Ollama / 社内 LLM）で動作し、クライアントは HTTP 経由でチャットするフロントエンドに徹する。
- 社内ユーザー向けに配布可能な単一 EXE（PyInstaller）としてパッケージングする。

### 0.3 想定利用シナリオ

- エンジニアやコンサルタントが、資料作成・コード補助・要約などの用途で、デスクトップ上から軽く LLM にアクセスする。
- 端末スペックや社内ソフトウェア制約により、ブラウザベースの重い Web UI や Electron アプリを避けたい場合の代替手段。

---

## 1. 要件定義

### 1.1 対象範囲（スコープ）

本仕様書のスコープは「Windows デスクトップ上で動く PySide6 アプリケーションのクライアント部分」のみとする。

- インスコープ
  - Python + PySide6 のシングルバイナリアプリ
  - LLM エンドポイントとの HTTP 通信
  - チャット UI（Markdown 表示）
  - シンプルな設定画面（エンドポイント URL、モデル名など）
  - ローカル設定ファイルの読み書き
- アウトオブスコープ（v0.1）
  - 複数プロファイル切り替え UI
  - ストリーミング表示（トークン逐次表示）
  - ホットキー起動、常駐トレイアイコン
  - 高度な会話履歴ブラウズ（複数セッション管理など）
  - 認証方式の実装詳細（必要なら後で社内仕様に合わせて拡張）

### 1.2 用語

- LLM エンドポイント
  - Ollama HTTP API、または OpenAI 互換などの社内 REST API。
- メッセージ
  - OpenAI 互換形式の `{role: "user" | "assistant" | "system", content: "..."}` のオブジェクト。
- セッション
  - アプリ起動中のチャット履歴全体（v0.1 では「マルチセッション」は扱わない）。

### 1.3 機能要件（Functional Requirements）

#### FR-1 チャット送受信

1. ユーザーはテキストを入力し「送信」ボタンで LLM エンドポイントに問い合わせできること。
2. アプリは以下の形式で LLM エンドポイントにリクエストすること（ベースラインとして OpenAI 互換を想定）:

   ```jsonc
   POST {base_url}/v1/chat/completions
   Authorization: Bearer {api_key} (任意、空でもよい)

   {
     "model": "{model_name}",
     "messages": [
       {"role": "system", "content": "..."}, // 任意
       {"role": "user", "content": "ユーザーの入力"},
       ...
     ]
   }
   ```

- Ollama 接続時には、必要に応じて `/api/chat` 形式などにマッピングできるよう抽象化する。

3. レスポンスは少なくとも以下を想定する：

   ```jsonc
   {
     "choices": [
       {
         "message": {
           "role": "assistant",
           "content": "..."
         }
       }
     ]
   }
   ```

4. レスポンスの `content` は Markdown として扱い、UI 上で Markdown レンダリングすること。

#### FR-2 チャット履歴表示

1. チャット画面には過去のユーザーメッセージと LLM 応答が時系列で表示されること。
2. 表示は Markdown としてレンダリングされること。
3. ユーザーとアシスタントの区別が視覚的に分かるよう、ラベル・改行・軽微な装飾を行うこと。

#### FR-3 設定管理

1. 以下の項目を設定画面で編集可能とする：

   - ベース URL（例：`http://localhost:11434` や `https://llm.example.com`）
   - モデル名（例：`llama3`, `gpt-4o-mini` など）
   - API キー（必要な場合、空でもよい）

2. 設定値はユーザーのローカル環境（ユーザープロファイル配下のファイル）に保存されること。
3. アプリ起動時に設定ファイルが存在すればそれを読み込み、存在しなければデフォルト値で初期化すること。

#### FR-4 エラーハンドリング

1. LLM エンドポイントへの接続失敗時（タイムアウト、DNS エラー、HTTP エラーなど）にはダイアログまたはステータスメッセージで通知すること。
2. 無効な設定（URL フォーマット不正など）の場合は、設定画面側でバリデーションし、ユーザーに分かりやすく伝えること。
3. 例外は落とさずに GUI 上にエラーを伝達し、アプリが異常終了しないようにすること。

#### FR-5 ローカル会話履歴（v0.1 は最小）

1. v0.1 では「アプリ起動中の履歴」が見られればよい（終了するとクリアで可）。
2. 任意（時間があれば）：セッション単位で JSON 保存する機能の下準備（`storage.py` に保存機能だけ生やしておく）。

### 1.4 非機能要件（Non-Functional Requirements）

#### NFR-1 パフォーマンス

1. コールドスタート（exe 起動 → ウィンドウ表示完了）

   - 目標: 2.0 秒以内（標準的な Windows 10/11, 8GB RAM 環境）。

2. 常駐時メモリ使用量

   - 目標: 300MB 以下（チャット数十メッセージ程度の状態で）。

3. CPU 使用率

   - アイドル時は数 % 程度に収まること。

#### NFR-2 対応 OS / ランタイム

1. Windows 10 / Windows 11 で動作すること。
2. 開発時のターゲット Python バージョンは 3.11 以降。
3. ランタイムとしては PyInstaller により exe 化し、クライアント環境に Python をインストールする必要がないこと。

#### NFR-3 セキュリティ / プライバシー

1. LLM との通信はユーザー端末からエンドポイントへの HTTPS / HTTP のみであり、第三者への中継は行わないこと（プロキシを除く）。
2. API キーはローカル設定ファイルに保存する際、最低限 OS のユーザープロファイル配下に保存し、他ユーザーから参照されないパスに置くこと。
3. v0.1 ではアプリ独自の暗号化までは求めないが、実装を簡単に拡張可能な構造にしておくこと。

#### NFR-4 メンテナビリティ / コーディング規約

1. Python コードは PEP8 準拠を基本とする。
2. 型ヒント（typing）を積極的に利用する。
3. 専用の `requirements.txt` または `pyproject.toml` を用意する。
4. ユニットテストは最低限 `client.py`（HTTP クライアント層）に対して用意する。

---

## 2. システムアーキテクチャ設計

### 2.1 全体構成

単一プロセスのデスクトップアプリとして構築する。

- プレゼンテーション層: PySide6 GUI
- アプリケーションロジック層: Chat セッション管理、UI ↔ LLM クライアントの仲介
- インフラ層: HTTP クライアント、設定ファイル I/O、（将来的な）履歴永続化

```text
[User]
   ↓
[PySide6 GUI (MainWindow)]
   ↓
[ChatController / ChatSession]
   ↓
[LlmClient (interface)]
   ├── OllamaClient
   └── OpenAiCompatibleClient
   ↓
[HTTP Endpoint (Ollama / 社内 LLM)]
```

### 2.2 使用技術

- 言語: Python 3.11+
- GUI: PySide6 (Qt6)

  - `QApplication`, `QMainWindow`, `QTextBrowser`, `QPlainTextEdit`, `QPushButton`, `QDialog`

- HTTP: `requests` または `httpx`（シンプルな同期通信で可）
- パッケージング: PyInstaller

### 2.3 モジュール構成

#### 2.3.1 `app.py`

- 役割

  - エントリポイント。
  - `QApplication` の生成、`MainWindow` のインスタンス化。

- 主な責務

  - 例外のトップレベルハンドリング（未処理例外時にユーザーに通知）。

#### 2.3.2 `ui_main.py`

- `MainWindow` クラス

  - GUI コンポーネントを組み立てる。

    - チャット表示ビュー（`QTextBrowser` または `QTextEdit` 読み取り専用）
    - 入力欄（`QPlainTextEdit`）
    - 送信ボタン（`QPushButton`）
    - メニューバー（設定ダイアログ呼び出し）

  - チャット履歴を Markdown として管理し、`setMarkdown()` で表示。
  - `LlmClient` を注入され、送信ボタン押下時に `send()` を呼ぶ。

- `SettingsDialog` クラス

  - ベース URL / モデル名 / API キーを編集。
  - OK ボタン押下で `config.py` を通じて保存。

#### 2.3.3 `client.py`

- `class BaseLlmClient(Protocol)` または抽象クラス

  - `send_chat(messages: list[Message]) -> str`

- `class OpenAiCompatibleClient(BaseLlmClient)`

  - `/v1/chat/completions` 形式の API を叩く。

- `class OllamaClient(BaseLlmClient)`

  - `/api/chat` 形式の API を叩く（必要に応じて）。

- 実装方針

  - v0.1 ではどちらか片方のみでもよい。
  - 将来的に複数クライアントを切り替えられるように設計しておく。

#### 2.3.4 `config.py`

- `load_config() -> Config`

  - `Config` は `dataclass` とし、URL, model, api_key 等をメンバーに持つ。

- `save_config(config: Config) -> None`
- 設定ファイルの場所

  - Windows のユーザープロファイル配下（例：`%APPDATA%\win-llm-chat-pyside\config.json`）

#### 2.3.5 `models.py`

- `@dataclass class Message`

  - `role: Literal["system", "user", "assistant"]`
  - `content: str`

- 必要であれば将来の拡張用に `ChatSession` などもここに定義。

#### 2.3.6 `storage.py`（将来拡張を見据えた枠だけ）

- v0.1 では以下の最低限を用意する：

  - `save_session(messages: list[Message], path: Path)`
  - `load_session(path: Path) -> list[Message]`

- 実装は単純な JSON ファイルで良い。

### 2.4 UI 仕様（簡易）

- メインウィンドウ

  - タイトルバー: アプリ名（仮: "LLM Chat Client"）
  - 上部チャットビュー:

    - Markdown 表示
    - スクロールバー有り

  - 下部入力エリア:

    - `QPlainTextEdit` で複数行入力
    - 右または下に「送信」ボタン

- メニュー

  - 「設定」メニュー → 「接続設定…」

    - ベース URL 入力欄
    - モデル名入力欄
    - API キー入力欄（パスワードモード）

### 2.5 シーケンス（送信時）

1. ユーザーが入力欄にテキストを入力し「送信」ボタンを押す。
2. `MainWindow` が内部の `messages` リストに `role="user"` の `Message` を追加。
3. `MainWindow` は `messages` を Markdown 文字列に変換し、`setMarkdown()` でビューを更新。
4. `MainWindow` は `LlmClient.send_chat(messages)` を呼び、レスポンス文字列（Markdown）を取得。
5. `messages` に `role="assistant"` の `Message` を追加。
6. 再度 Markdown を生成し `setMarkdown()` で更新。

v0.1 では同期呼び出しでよいが、応答時間が気になる場合は後続バージョンで `QThread` 化する。

---

## 3. タスク一覧（Cursor 向けブレイクダウン）

### 3.0 リポジトリセットアップ

- [ ] `poetry` または `pip` + `requirements.txt` で Python 環境を定義

  - 依存: `PySide6`, `requests` または `httpx`

- [ ] `.gitignore` 設定（`__pycache__`, `.venv`, `dist`, `build` 等）
- [ ] `src/` ディレクトリ構造を作成

  - `src/app.py`
  - `src/ui_main.py`
  - `src/client.py`
  - `src/config.py`
  - `src/models.py`
  - `src/storage.py`（空の枠だけでも可）

- [ ] 基本的な README（セットアップ方法、実行方法）

### 3.1 PySide6 アプリ骨格

- [ ] `app.py` にエントリポイントを実装

  - `QApplication` の生成
  - `MainWindow` 起動

- [ ] `MainWindow` クラスの雛形を `ui_main.py` に作成

  - チャットビュー（`QTextBrowser`）と入力欄（`QPlainTextEdit`）、送信ボタンを配置
  - 送信ボタン押下で入力欄の内容をチャットビューに表示するだけの仮実装

### 3.2 設定管理 (`config.py`)

- [ ] `Config` dataclass の定義

  - `base_url: str`
  - `model: str`
  - `api_key: str | None`

- [ ] ユーザープロファイル下に設定ファイルを置くロジックを実装

  - Windows の `%APPDATA%` を利用

- [ ] `load_config` / `save_config` 実装

  - JSON 形式で読み書き

### 3.3 LLM クライアント (`client.py`)

- [ ] `Message` dataclass を `models.py` に定義
- [ ] `BaseLlmClient` インターフェース（Protocol or ABC）定義

  - `send_chat(messages: list[Message]) -> str`

- [ ] `OpenAiCompatibleClient` 実装

  - `POST {base_url}/v1/chat/completions`
  - リクエストボディ・レスポンスパース

- [ ] 必要に応じて `OllamaClient` を追加実装（インターフェースは同じ）

### 3.4 MainWindow と LlmClient の統合

- [ ] `MainWindow` に `LlmClient` インスタンスを注入
- [ ] ユーザー入力を `Message(role="user")` に変換し、内部 `messages` リストに追加
- [ ] `messages` リストから Markdown 文字列を生成し、`QTextBrowser.setMarkdown()` で更新
- [ ] `LlmClient.send_chat(messages)` を呼び出し、レスポンスを `Message(role="assistant")` として追加
- [ ] 再度 Markdown を生成して `setMarkdown()` で更新
- [ ] 送信中は送信ボタンを disable し、処理終了後に enable に戻す

### 3.5 設定ダイアログ (`SettingsDialog`)

- [ ] `SettingsDialog` クラスを `ui_main.py` に実装

  - `QLineEdit` で base_url, model, api_key を編集

- [ ] メニューバーに「設定」メニューを追加し、ダイアログを起動
- [ ] OK 押下で `Config` を保存し、`MainWindow` 側に変更を反映

  - （v0.1 では設定変更時に LlmClient を作り直せばよい）

### 3.6 エラーハンドリング

- [ ] `LlmClient` 内での例外を捕捉し、意味のあるエラーメッセージに変換
- [ ] `MainWindow` 側でエラーを受け取り、`QMessageBox` などでユーザーに通知
- [ ] ネットワークエラー・認証エラー・フォーマットエラーなど代表的なケースに対応

### 3.7 パッケージング（PyInstaller）

- [ ] PyInstaller の spec ファイルを作成

  - `console=False` で GUI アプリとしてビルド

- [ ] `build` / `dist` ディレクトリに exe を出力
- [ ] 生成された exe を別の Windows マシンで動作確認

  - 起動時間
  - メモリ使用量
  - LLM への接続確認

### 3.8 簡易テスト

- [ ] `client.py` に対してユニットテストを追加

  - HTTP レスポンスをモックし、正しくメッセージを組み立てているか検証

- [ ] 手動テスト項目

  - 正常系: 送信 → 応答 →Markdown 表示
  - 異常系: URL 不正 / API キー未設定 / 接続エラー

---

## 4. 実装上のガイドライン（Cursor への指示）

1. コードスタイル

   - PEP8 準拠、型ヒント必須。
   - ファイル先頭に簡単なモジュール概要 docstring を記載すること。

2. 依存ライブラリ

   - 最小限に抑えること（PySide6 + requests/httpx 程度）。
   - 不要なフレームワーク（Flask, FastAPI など）はクライアント側には入れないこと。

3. テスト

   - 重要なロジック（HTTP リクエスト組み立て、レスポンスパース）はユニットテストでカバーすること。

4. 拡張性

   - 将来的に複数の LLM エンドポイントに対応できるよう、`LlmClient` はインターフェース + 実装の形を守ること。
   - セッション永続化（`storage.py`）は枠だけ用意し、ロジックは簡素でよい。

以上。

```

```
