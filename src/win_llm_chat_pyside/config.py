"""
設定の読み書きを管理する。
"""

import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, Literal, List, Tuple


@dataclass
class Profile:
    """接続先プロファイル。"""
    name: str
    type: Literal["openai", "ollama"] = "openai"
    base_url: str = "http://localhost:11434"
    model: str = "gemma3:4b"
    api_key: Optional[str] = None
    # 将来拡張用に余地を残す
    extras: dict | None = None


@dataclass
class Config:
    """アプリケーション設定を保持するデータクラス。"""
    base_url: str = "http://localhost:11434"
    model: str = "gemma3:4b"
    api_key: Optional[str] = None
    # v0.5: 複数プロファイル対応
    profiles: List[Profile] = field(default_factory=list)
    current_profile_name: Optional[str] = None

    # UI/ネットワーク拡張（既定値で後方互換）
    request_timeout_ms: int = 30000
    connect_timeout_ms: int = 10000
    # ストリーミング用の個別タイムアウト（未設定時は上記を流用）
    stream_total_timeout_ms: int = 30000
    stream_connect_timeout_ms: int = 5000
    ui_enter_to_send: bool = False
    ui_ctrl_enter_to_send: bool = True
    ui_autoscroll_enabled: bool = True
    ui_wait_indicator_style: str = "spinner"
    ui_markdown_font_family: str = "Segoe UI"
    ui_markdown_font_size_pt: int = 11
    ui_markdown_line_height: float = 1.6
    # ストリーミング UI
    ui_streaming_stop_enabled: bool = True
    ui_streaming_chunk_render_interval_ms: int = 0

    # ウィンドウ操作
    global_hotkey_enabled: bool = True
    global_hotkey_combination: str = "Ctrl+Alt+Space"
    always_on_top: bool = False

    # 履歴保存/エクスポート（v0.4）
    history_enabled: bool = True
    history_format: Literal["json", "markdown"] = "json"
    history_path: Optional[str] = None  # 既定はアプリデータ配下
    history_max_messages: int = 400
    history_max_chars: int = 200_000
    export_default_dir: Optional[str] = None
    export_filename_pattern: str = "Chat-{yyyy-MM-dd HH-mm}.md"
    # 観測性（v0.6）
    logging_enabled: bool = True
    logging_level: str = "info"
    logging_dir: Optional[str] = None  # 既定はアプリデータ配下の logs ディレクトリ
    logging_max_file_size_mb: int = 5
    logging_rotation_keep_files: int = 5
    diagnostics_show_env_details: bool = False
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        設定値を検証する。
        
        Returns:
            (is_valid, error_message) のタプル
        """
        # プロファイルがある場合はカレントプロファイルを検証する
        if self.profiles and self.current_profile_name:
            prof = get_current_profile(self)
            if not prof:
                return False, "現在のプロファイルが見つかりません"
            return validate_profile(prof)
        # 後方互換：単一設定を検証
        if not self.base_url or not self.base_url.strip():
            return False, "ベース URL が空です"
        if not self.base_url.startswith(("http://", "https://")):
            return False, "ベース URL は http:// または https:// で始まる必要があります"
        if not self.model or not self.model.strip():
            return False, "モデル名が空です"
        
        return True, None


def get_config_path() -> Path:
    """
    設定ファイルのパスを取得する。
    
    Windows の場合は %APPDATA%/win-llm-chat-pyside/config.json
    """
    config_dir = get_data_dir()
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.json"

def get_data_dir() -> Path:
    """
    アプリケーションのデータディレクトリを返す。
    Windows: %APPDATA%/win-llm-chat-pyside
    """
    if os.name == "nt":  # Windows
        appdata = os.getenv("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA 環境変数が設定されていません")
        return Path(appdata) / "win-llm-chat-pyside"
    # Linux/Mac（将来拡張）
    return Path.home() / ".config" / "win-llm-chat-pyside"

def get_default_history_path() -> Path:
    """
    既定の履歴保存パス（単一セッション）を返す。
    例: %APPDATA%/win-llm-chat-pyside/history/session.json
    """
    base = get_data_dir()
    history_dir = base / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir / "session.json"


def get_sessions_dir(config: Optional[Config] = None) -> Path:
    """
    マルチセッション保存用ディレクトリを返す。
    履歴パスが設定されている場合はその親配下に sessions/ を作成する。
    """
    if config and config.history_path:
        base = Path(config.history_path).expanduser().resolve().parent / "sessions"
    else:
        base = get_data_dir() / "sessions"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_prompt_assets_dir(config: Optional[Config] = None) -> Path:
    """
    プロンプトテンプレート/役割プロファイルの保存ディレクトリ。
    履歴パスに依存させず、データディレクトリ配下に prompt_assets/ を切る。
    """
    base = get_data_dir()
    if config and config.history_path:
        try:
            base = Path(config.history_path).expanduser().resolve().parent
        except Exception:
            pass
    assets_dir = base / "prompt_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    return assets_dir


def get_default_logs_dir() -> Path:
    """
    ログファイルの既定ディレクトリを返す。
    例: %APPDATA%/win-llm-chat-pyside/logs
    """
    base = get_data_dir()
    logs_dir = base / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir

def load_config() -> Config:
    """
    設定ファイルを読み込む。存在しない場合はデフォルト値を返す。
    
    Returns:
        Config インスタンス
    """
    config_path = get_config_path()
    
    if not config_path.exists():
        # 新規は既定の設定（後段で migrate して profiles[0]=default 化可能）
        return Config()
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # v0.5: 移行は Repository に委譲
        try:
            from . import profile_repository as repo
            cfg = repo.migrate_if_needed(data)  # type: ignore[assignment]
        except Exception:
            # フォールバック（Repository 未導入でも動作）
            cfg = _config_from_dict(data)
            _migrate_single_to_profiles_if_needed(cfg)
        return cfg
    except (json.JSONDecodeError, TypeError) as e:
        print(f"設定ファイルの読み込みに失敗しました: {e}")
        return Config()


def save_config(config: Config) -> None:
    """
    設定をファイルに保存する。
    
    Args:
        config: 保存する Config インスタンス
    """
    # Repository に委譲（原子的保存）
    try:
        from . import profile_repository as repo
        repo.save_full_config(config)
        return
    except Exception:
        pass
    # フォールバック（Repository 未導入でも動作）
    config_path = get_config_path()
    tmp_path = config_path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, config_path)


# ---- v0.5: プロファイル関連ヘルパ ----
def _config_from_dict(data: dict) -> Config:
    """dict から Config を生成。profiles を明示復元。"""
    profiles_data = data.get("profiles") or []
    profiles: list[Profile] = []
    for p in profiles_data:
        try:
            profiles.append(Profile(
                name=p["name"],
                type=p.get("type", "openai"),
                base_url=p.get("base_url") or data.get("base_url", "http://localhost:11434"),
                model=p.get("model") or data.get("model", "gemma3:4b"),
                api_key=p.get("api_key"),
                extras=p.get("extras"),
            ))
        except KeyError:
            continue
    cfg = Config(
        base_url=data.get("base_url", "http://localhost:11434"),
        model=data.get("model", "gemma3:4b"),
        api_key=data.get("api_key"),
        profiles=profiles,
        current_profile_name=data.get("current_profile_name"),
        request_timeout_ms=int(data.get("request_timeout_ms", 30000)),
        connect_timeout_ms=int(data.get("connect_timeout_ms", 10000)),
        stream_total_timeout_ms=int(data.get("stream_total_timeout_ms", 30000)),
        stream_connect_timeout_ms=int(data.get("stream_connect_timeout_ms", 5000)),
        ui_enter_to_send=bool(data.get("ui_enter_to_send", False)),
        ui_ctrl_enter_to_send=bool(data.get("ui_ctrl_enter_to_send", True)),
        ui_autoscroll_enabled=bool(data.get("ui_autoscroll_enabled", True)),
        ui_wait_indicator_style=data.get("ui_wait_indicator_style", "spinner"),
        ui_markdown_font_family=data.get("ui_markdown_font_family", "Segoe UI"),
        ui_markdown_font_size_pt=int(data.get("ui_markdown_font_size_pt", 11)),
        ui_markdown_line_height=float(data.get("ui_markdown_line_height", 1.6)),
        ui_streaming_stop_enabled=bool(data.get("ui_streaming_stop_enabled", True)),
        ui_streaming_chunk_render_interval_ms=int(data.get("ui_streaming_chunk_render_interval_ms", 0)),
        global_hotkey_enabled=bool(data.get("global_hotkey_enabled", True)),
        global_hotkey_combination=data.get("global_hotkey_combination", "Ctrl+Alt+Space") or "Ctrl+Alt+Space",
        always_on_top=bool(data.get("always_on_top", False)),
        history_enabled=bool(data.get("history_enabled", True)),
        history_format=data.get("history_format", "json"),
        history_path=data.get("history_path"),
        history_max_messages=int(data.get("history_max_messages", 400)),
        history_max_chars=int(data.get("history_max_chars", 200_000)),
        export_default_dir=data.get("export_default_dir"),
        export_filename_pattern=data.get("export_filename_pattern", "Chat-{yyyy-MM-dd HH-mm}.md"),
        logging_enabled=bool(data.get("logging_enabled", True)),
        logging_level=str(data.get("logging_level", "info")),
        logging_dir=data.get("logging_dir"),
        logging_max_file_size_mb=int(data.get("logging_max_file_size_mb", 5)),
        logging_rotation_keep_files=int(data.get("logging_rotation_keep_files", 5)),
        diagnostics_show_env_details=bool(data.get("diagnostics_show_env_details", False)),
    )
    return cfg


def _migrate_single_to_profiles_if_needed(config: Config) -> None:
    """
    旧スキーマ（単一 base_url/model）から profiles[0] への冪等移行。
    既に profiles があれば何もしない。
    """
    if config.profiles:
        # 既に移行済み
        return
    # base_url/model が設定されているなら、それを profiles[0] として取り込む
    default_name = "default"
    prof = Profile(
        name=default_name,
        type="openai",  # 後方互換として openai とみなす
        base_url=config.base_url,
        model=config.model,
        api_key=config.api_key,
    )
    config.profiles = [prof]
    config.current_profile_name = default_name


def get_current_profile(config: Config) -> Optional[Profile]:
    """現在選択中のプロファイルを返す。見つからなければ None。"""
    if not config.profiles or not config.current_profile_name:
        return None
    for p in config.profiles:
        if p.name == config.current_profile_name:
            return p
    return None


def validate_profile(profile: Profile) -> Tuple[bool, Optional[str]]:
    """プロファイルの検証。"""
    if not profile.name or not profile.name.strip():
        return False, "プロファイル名が空です"
    if profile.type not in ("openai", "ollama"):
        return False, "type は openai または ollama を指定してください"
    if not profile.base_url or not profile.base_url.strip():
        return False, "ベース URL が空です"
    if not profile.base_url.startswith(("http://", "https://")):
        return False, "ベース URL は http:// または https:// で始まる必要があります"
    if not profile.model or not profile.model.strip():
        return False, "モデル名が空です"
    return True, None

