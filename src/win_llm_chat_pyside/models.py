"""
ドメインモデルを定義する。
"""

from dataclasses import dataclass, field
from typing import Dict, Literal, List


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
    role_profile_id: str | None = None
    attachments: List["AttachmentMetadata"] = field(default_factory=list)
    attachment_texts: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages],
            "role_profile_id": self.role_profile_id,
            "attachments": [attachment.to_dict() for attachment in self.attachments],
            "attachment_texts": dict(self.attachment_texts),
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
        attachments_data = data.get("attachments", [])
        attachments = [
            AttachmentMetadata.from_dict(item)
            for item in attachments_data
            if isinstance(item, dict)
        ]
        attachment_texts = data.get("attachment_texts") or {}
        if not isinstance(attachment_texts, dict):
            attachment_texts = {}
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            messages=messages,
            role_profile_id=data.get("role_profile_id"),
            attachments=attachments,
            attachment_texts={str(k): str(v) for k, v in attachment_texts.items()},
        )


@dataclass
class SessionSummary:
    """セッション一覧検索用の軽量サマリ。"""

    id: str
    name: str
    updated_at: str
    preview_text: str


@dataclass
class PromptTemplate:
    """ユーザーが再利用するプロンプトテンプレート。"""

    id: str
    title: str
    body: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PromptTemplate":
        return cls(
            id=data["id"],
            title=data["title"],
            body=data.get("body", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class RoleProfile:
    """セッション作成時に適用する system prompt プロファイル。"""

    id: str
    name: str
    system_prompt: str
    created_at: str
    updated_at: str
    is_default: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "system_prompt": self.system_prompt,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_default": self.is_default,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RoleProfile":
        return cls(
            id=data["id"],
            name=data["name"],
            system_prompt=data.get("system_prompt", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            is_default=bool(data.get("is_default", False)),
        )


AttachmentStatus = Literal["pending", "extracting", "ready", "failed"]


@dataclass
class AttachmentMetadata:
    """セッションに紐づく添付ファイルのメタ情報。"""

    id: str
    session_id: str
    filename: str
    size_bytes: int
    mime_type: str
    page_count: int | None = None
    text_length: int | None = None
    status: AttachmentStatus = "pending"
    error_message: str | None = None
    length_warning: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "mime_type": self.mime_type,
            "page_count": self.page_count,
            "text_length": self.text_length,
            "status": self.status,
            "error_message": self.error_message,
            "length_warning": self.length_warning,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AttachmentMetadata":
        return cls(
            id=data["id"],
            session_id=data.get("session_id", ""),
            filename=data.get("filename", ""),
            size_bytes=int(data.get("size_bytes", 0)),
            mime_type=data.get("mime_type", ""),
            page_count=data.get("page_count"),
            text_length=data.get("text_length"),
            status=data.get("status", "pending"),
            error_message=data.get("error_message"),
            length_warning=bool(data.get("length_warning", False)),
        )


