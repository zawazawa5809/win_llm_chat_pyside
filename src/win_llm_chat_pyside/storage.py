"""
将来の履歴永続化機能のためのスタブ。

v0.1 では実装は最小限とし、将来の拡張に備えた API のみを定義する。
"""

from pathlib import Path
from typing import List
import json

from .models import Message


def save_session(messages: List[Message], path: Path) -> None:
    """
    セッション（メッセージリスト）をファイルに保存する。
    
    Args:
        messages: 保存するメッセージのリスト
        path: 保存先のファイルパス
    
    Note:
        v0.1 では基本的な JSON 保存のみ実装。
        将来的にはローテーション、圧縮、検索機能などを追加予定。
    """
    data = [msg.to_dict() for msg in messages]
    
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_session(path: Path) -> List[Message]:
    """
    ファイルからセッション（メッセージリスト）を読み込む。
    
    Args:
        path: 読み込むファイルパス
        
    Returns:
        メッセージのリスト
        
    Raises:
        FileNotFoundError: ファイルが存在しない場合
        json.JSONDecodeError: JSON 形式が不正な場合
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return [Message.from_dict(item) for item in data]


# 将来の拡張候補:
# - list_sessions(): 保存済みセッションの一覧取得
# - delete_session(session_id): セッション削除
# - search_sessions(query): セッション検索
# - export_session(session_id, format): エクスポート（Markdown, PDF など）


