"""
将来の履歴永続化機能のためのスタブ。

v0.1 では実装は最小限とし、将来の拡張に備えた API のみを定義する。
"""

from pathlib import Path
from typing import List, Iterable, Dict, Any
import json
import os
from datetime import datetime

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


def save_session_atomic(messages: List[Message], path: Path) -> None:
    """
    セッションを原子的に保存する。既存があれば .bak を1世代保持する。
    """
    data = [msg.to_dict() for msg in messages]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    bak_path = path.with_suffix(path.suffix + ".bak")

    # 事前にバックアップを作成（存在時）
    if path.exists():
        try:
            # 既存の .bak は上書き
            if bak_path.exists():
                try:
                    os.remove(bak_path)
                except OSError:
                    pass
            os.replace(path, bak_path)
        except OSError:
            # バックアップ失敗は続行（致命ではない）
            pass

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # 同一ディレクトリ内で置換
    os.replace(tmp_path, path)


def load_session_safe(path: Path) -> List[Message]:
    """
    セッションを読み込む（例外は呼び出し側でハンドリング）。
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Message.from_dict(item) for item in data]


def render_markdown(messages: Iterable[Message], metadata: Dict[str, Any] | None = None) -> str:
    """
    会話を Markdown 文字列に整形する。簡易なメタ情報ヘッダを付与する。
    """
    parts: list[str] = []
    meta = dict(metadata or {})
    meta.setdefault("exported_at", datetime.now().isoformat(timespec="seconds"))
    # メタ情報ヘッダ
    parts.append("# Chat Export\n\n")
    if meta:
        parts.append("<!-- metadata -->\n")
        for k, v in meta.items():
            parts.append(f"- {k}: {v}\n")
        parts.append("\n")

    for msg in messages:
        role = "User" if msg.role == "user" else ("Assistant" if msg.role == "assistant" else "System")
        parts.append(f"\n**{role}:**\n\n{msg.content}\n")
    return "".join(parts)


def export_markdown_file(messages: Iterable[Message], path: Path, metadata: Dict[str, Any] | None = None) -> None:
    """
    会話を Markdown ファイルへ書き出す。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    content = render_markdown(messages, metadata=metadata)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def calculate_history_size(messages: Iterable[Message]) -> tuple[int, int]:
    """
    履歴サイズを (メッセージ数, 総文字数) で返す。
    """
    count = 0
    total_chars = 0
    for m in messages:
        count += 1
        total_chars += len(m.content)
    return count, total_chars

# 将来の拡張候補:
# - list_sessions(): 保存済みセッションの一覧取得
# - delete_session(session_id): セッション削除
# - search_sessions(query): セッション検索
# - export_session(session_id, format): エクスポート（Markdown, PDF など）


