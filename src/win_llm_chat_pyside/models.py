"""
ドメインモデルを定義する。
"""

from dataclasses import dataclass
from typing import Literal


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


