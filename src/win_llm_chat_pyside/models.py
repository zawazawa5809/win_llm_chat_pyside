"""
ドメインモデルを定義する。
"""

from dataclasses import dataclass, field
from typing import Literal, List


@dataclass
class Message:
    """LLM とのチャットメッセージを表すモデル。"""
    role: Literal["system", "user", "assistant"]
    content: str
    
    def to_dict(self) -> dict:
        """辞書形式に変換する（API リクエスト用）。"""
        return {
            "role": self.role,
            "content": self.content
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """辞書から Message を生成する。"""
        return cls(
            role=data["role"],
            content=data["content"]
        )


@dataclass
class SessionMeta:
    """セッション一覧で使用する軽量メタ情報。"""

    id: str
    name: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionMeta":
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


@dataclass
class Session:
    """メッセージ履歴とメタ情報を含むセッション。"""

    id: str
    name: str
    created_at: str
    updated_at: str
    messages: List[Message] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages],
        }

    def to_meta(self) -> SessionMeta:
        return SessionMeta(
            id=self.id,
            name=self.name,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        messages = [Message.from_dict(item) for item in data.get("messages", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            messages=messages,
        )


