# ディレクトリ構成リファクタリング計画

## 1. 背景と目的

現在の `src/win_llm_chat_pyside` は、40以上のファイルが単一階層に混在する「フラット構造」となっています。
プロジェクトの成長に伴い、以下の問題が顕在化しています：

1. **責務の混在**: UI、ビジネスロジック、インフラストラクチャが混ざり合い、変更の影響範囲が予測しづらい。
2. **God Class の存在**: 特に `ui_main.py` が巨大化し、あらゆる機能への依存が集まっている。
3. **認知負荷**: 機能を探すために大量のファイルリストを目視スキャンする必要がある。

本計画では、「機能によるグループ化（Package by Feature）」を軸としたディレクトリ構造へ移行し、拡張性と保守性を確保することを目的とします。

## 2. 目標ディレクトリ構造

アプリケーションを「コア」「機能」「UI」「サービス」「モデル」の5つの領域に分類します。

```text
src/win_llm_chat_pyside/
├── core/                 # アプリケーションの核となる設定・起動処理
│   ├── app.py            # エントリポイント
│   ├── config.py         # 設定管理
│   ├── app_logger.py     # ロギング
│   └── factory.py        # DIコンテナ・初期化
│
├── features/             # 機能ごとの独立したモジュール（View + Logic）
│   ├── chat/             # チャット機能
│   │   ├── composer.py   # メッセージ入力
│   │   ├── view.py       # チャット表示
│   │   └── logic.py      # チャットロジック
│   ├── sessions/         # セッション管理
│   ├── attachments/      # 添付ファイル処理
│   ├── prompts/          # プロンプトテンプレート
│   └── roles/            # 役割プロファイル
│
├── ui/                   # 共通UIコンポーネント・メインウィンドウ
│   ├── common/           # 汎用ウィジェット（特定機能に依存しない）
│   ├── dialogs/          # 汎用ダイアログ
│   ├── main_window.py    # アプリケーションシェル（旧 ui_main.py）
│   └── styles/           # テーマ・スタイル定義
│
├── services/             # インフラ・外部連携
│   ├── llm_client.py     # APIクライアント
│   ├── storage.py        # ローカルファイル永続化
│   └── clipboard.py      # クリップボード操作
│
└── models/               # 共通データモデル
    └── ...               # アプリ全体で共有される型定義
```

## 3. 設計原則と境界ルール

リファクタリング後の秩序を保つため、以下のルールを適用します。

### 3.1. Features (機能モジュール)
- **原則**: `features/xxx` は、その機能に関する UI（Widget）とロジック（Service/Manager）を完結させる。
- **依存**: 他の `features` を直接 import することを避ける。必要な場合は `services` やシグナル、共通モデルを介して連携する。
- **公開**: 外部から利用されるコンポーネントや関数のみを `__init__.py` で公開し、内部実装は隠蔽する。

### 3.2. UI (共通UI)
- **範囲**: アプリケーション全体のレイアウト、テーマ、および「特定の機能ドメインを知らない」汎用部品のみを置く。
- **禁止**: `ui/` 配下のコンポーネントが `features/` 配下の具体的なロジックに依存してはならない（循環参照の温床となるため）。

### 3.3. Models (共通モデル)
- **範囲**: `Session`, `Message` など、アプリケーションの全域で参照されるコアエンティティのみを置く。
- **特定機能のモデル**: 特定の feature だけで使われるモデル（例: `PendingClipboardImage`）は、`features/xxx/models.py` に配置する。

### 3.4. Services (インフラ)
- **範囲**: 外部 API、ファイルシステム、OS 機能へのアクセスを担当する。
- **依存**: 原則として `ui` や `features` に依存しない（Models への依存は可）。

## 4. 移行フェーズ（Migration Phases）

リスクを最小化するため、以下の段階的アプローチで実施します。

### Phase 1: 末端モジュールの整理
依存関係が少なく、移動が容易なモジュールから着手します。

- [ ] **Models**: `models.py` を `models/` パッケージへ移動（必要に応じて分割）。
- [ ] **Prompts**: `prompt_*.py` を `features/prompts/` へ移動。
- [ ] **Roles**: `role_*.py` を `features/roles/` へ移動。
- [ ] **Search**: `search_services.py` 等を `features/search/` へ移動。

### Phase 2: コアとサービスの分離
アプリの基盤部分を明確にします。

- [ ] **Core**: `config.py`, `app_logger.py`, `factory.py` を `core/` へ移動。
- [ ] **Services**: `client.py`, `storage.py`, `global_hotkey.py`, `clipboard_images.py` を `services/` へ移動。

### Phase 3: 主要機能のモジュール化
ビジネスロジックの中核を移動します。ここが最も複雑になります。

- [ ] **Attachments**: `attachment_*.py`, `attachments.py` を `features/attachments/` へ移動。
- [ ] **Sessions**: `session_*.py`, `session_manager.py` を `features/sessions/` へ移動。
- [ ] **Chat**: `chat_*.py`, `message_composer.py` を `features/chat/` へ移動。

### Phase 4: UI層の再構築
最後に残った `ui_main.py` を軽量化・移動します。

- [ ] **UI**: `ui_main.py` を `ui/main_window.py` にリネームして移動。
- [ ] **Styles**: `theme.py`, `layout_*.py` を `ui/` 配下へ整理。
- [ ] **Decoupling**: `ui_main.py` に残ったロジックを各 feature へ委譲（継続的リファクタリング）。

## 5. 作業ガイドライン

1. **Git操作**: ファイル移動には必ず `git mv` を使用し、履歴を追跡可能にする。
2. **テスト実行**: 各 Phase 完了ごとに `pytest` をフル実行し、import エラーやパス依存のテスト落ちがないか確認する。
3. **Import修正**: ファイル移動に伴い、全ファイルの import パス修正が必要になる。一括置換ツールを活用しつつ、手動確認を行う。
4. **循環参照**: 移動によって隠れていた循環参照が顕在化した場合、`TYPE_CHECKING` ブロックの活用やインターフェース分離を行う。

