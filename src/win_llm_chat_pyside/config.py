"""
設定の読み書きを管理する。
"""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """アプリケーション設定を保持するデータクラス。"""
    base_url: str = "http://localhost:11434"
    model: str = "gemma3:4b"
    api_key: Optional[str] = None

    # UI/ネットワーク拡張（既定値で後方互換）
    request_timeout_ms: int = 30000
    connect_timeout_ms: int = 10000
    ui_enter_to_send: bool = False
    ui_ctrl_enter_to_send: bool = True
    ui_autoscroll_enabled: bool = True
    ui_wait_indicator_style: str = "spinner"
    ui_markdown_font_family: str = "Segoe UI"
    ui_markdown_font_size_pt: int = 11
    ui_markdown_line_height: float = 1.6
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        設定値を検証する。
        
        Returns:
            (is_valid, error_message) のタプル
        """
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
    if os.name == "nt":  # Windows
        appdata = os.getenv("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA 環境変数が設定されていません")
        config_dir = Path(appdata) / "win-llm-chat-pyside"
    else:
        # Linux/Mac の場合（将来の拡張用）
        config_dir = Path.home() / ".config" / "win-llm-chat-pyside"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.json"


def load_config() -> Config:
    """
    設定ファイルを読み込む。存在しない場合はデフォルト値を返す。
    
    Returns:
        Config インスタンス
    """
    config_path = get_config_path()
    
    if not config_path.exists():
        return Config()
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Config(**data)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"設定ファイルの読み込みに失敗しました: {e}")
        return Config()


def save_config(config: Config) -> None:
    """
    設定をファイルに保存する。
    
    Args:
        config: 保存する Config インスタンス
    """
    config_path = get_config_path()
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f, indent=2, ensure_ascii=False)


