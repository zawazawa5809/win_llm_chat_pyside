"""
添付ファイルの管理とテキスト抽出を担当するモジュール。
"""

from __future__ import annotations

import mimetypes
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from win_llm_chat_pyside.core.app_logger import app_logger
from win_llm_chat_pyside.models import AttachmentMetadata, Session
from win_llm_chat_pyside.features.sessions.session_manager import SessionManager

try:  # pragma: no cover - import guard
    from pypdf import PdfReader as _PdfReader  # type: ignore[import-untyped]
except Exception:  # noqa: BLE001
    _PdfReader = None  # type: ignore[assignment,misc]

# 公開属性としてエクスポートし、テストから monkeypatch できるようにする
PdfReader = _PdfReader


class AttachmentError(Exception):
    """添付ファイル処理に関する基底例外。"""


class AttachmentExtractionError(AttachmentError):
    """テキスト抽出に失敗した場合の例外。"""


@dataclass
class ExtractionResult:
    """テキスト抽出の結果。"""

    text: str
    page_count: int | None = None


class FileTextExtractor:
    """テキスト / PDF から文字列を抽出するユーティリティ。"""

    _TEXT_EXTENSIONS = {".txt", ".text", ".md", ".markdown", ".log"}

    def extract_text(self, path: Path) -> ExtractionResult:
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix in self._TEXT_EXTENSIONS:
            text = self._read_text_file(path)
            return ExtractionResult(text=text, page_count=None)
        if suffix == ".pdf":
            return self._extract_pdf(path)
        raise AttachmentExtractionError(f"未対応のファイル形式です: {suffix or path.name}")

    def _read_text_file(self, path: Path) -> str:
        encodings = ("utf-8", "utf-16", "cp932")
        for encoding in encodings:
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return path.read_text(encoding="utf-8", errors="ignore")

    def _extract_pdf(self, path: Path) -> ExtractionResult:
        if PdfReader is None:  # pragma: no cover - guard path
            raise AttachmentExtractionError("PDF 抽出には pypdf が必要です")
        try:
            reader = PdfReader(path)
        except Exception as exc:  # noqa: BLE001
            raise AttachmentExtractionError(f"PDF の読み込みに失敗しました: {exc}") from exc
        texts: list[str] = []
        for page in reader.pages:
            try:
                extracted = page.extract_text() or ""
            except Exception as exc:  # noqa: BLE001
                raise AttachmentExtractionError(f"PDF からテキストを抽出できませんでした: {exc}") from exc
            if extracted:
                texts.append(extracted.strip())
        combined = "\n\n".join(chunk for chunk in texts if chunk).strip()
        return ExtractionResult(text=combined, page_count=len(reader.pages))


class AttachmentManager:
    """セッション単位の添付ファイル管理とテキスト抽出を調停する。"""

    def __init__(
        self,
        session_manager: SessionManager,
        text_extractor: Optional[FileTextExtractor] = None,
        *,
        max_text_length: int = 20_000,
    ) -> None:
        self._session_manager = session_manager
        self._extractor = text_extractor or FileTextExtractor()
        self._max_text_length = max_text_length

    def list_attachments(self, session_id: str) -> list[AttachmentMetadata]:
        session = self._session_manager.load_session(session_id)
        return list(session.attachments)

    def add_attachment(
        self,
        session_id: str,
        file_path: Path,
        *,
        source: str = "user_file",
        stored_file_path: str | None = None,
        skip_text_extraction: bool = False,
    ) -> AttachmentMetadata:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(path)

        session = self._session_manager.load_session(session_id)
        metadata = AttachmentMetadata(
            id=self._generate_id(),
            session_id=session_id,
            filename=path.name,
            size_bytes=path.stat().st_size,
            mime_type=self._guess_mime_type(path),
            status="pending",
            source=source,  # type: ignore[arg-type]
            stored_file_path=stored_file_path,
        )
        session.attachments.append(metadata)
        self._session_manager.update_session(session)
        if skip_text_extraction:
            metadata.status = "ready"
            self._session_manager.update_session(session)
            return metadata
        return self._extract_and_store_text(session_id, metadata.id, path)

    def refresh_attachment(self, session_id: str, attachment_id: str, file_path: Path) -> AttachmentMetadata:
        """既存添付の再抽出。"""
        return self._extract_and_store_text(session_id, attachment_id, Path(file_path))

    def remove_attachment(self, session_id: str, attachment_id: str) -> None:
        session = self._session_manager.load_session(session_id)
        removed: AttachmentMetadata | None = None
        remaining: list[AttachmentMetadata] = []
        for attachment in session.attachments:
            if attachment.id == attachment_id:
                removed = attachment
                continue
            remaining.append(attachment)
        session.attachments = remaining
        session.attachment_texts.pop(attachment_id, None)
        self._session_manager.update_session(session)
        if removed and removed.stored_file_path:
            self._delete_stored_file(removed.stored_file_path)

    # ---- internal helpers ----
    def _extract_and_store_text(self, session_id: str, attachment_id: str, path: Path) -> AttachmentMetadata:
        session = self._session_manager.load_session(session_id)
        attachment = self._find_attachment(session, attachment_id)
        attachment.status = "extracting"
        attachment.error_message = None
        self._session_manager.update_session(session)

        try:
            result = self._extractor.extract_text(path)
        except AttachmentExtractionError as exc:
            attachment.status = "failed"
            attachment.error_message = str(exc)
            self._session_manager.update_session(session)
            try:
                app_logger.warning(
                    "attachment.extract_failed",
                    {"session_id": session_id, "attachment_id": attachment_id, "error": str(exc)},
                )
            except Exception:  # noqa: BLE001
                pass
            return attachment

        attachment.status = "ready"
        attachment.page_count = result.page_count
        attachment.text_length = len(result.text)
        attachment.length_warning = bool(
            attachment.text_length and attachment.text_length > self._max_text_length
        )
        session.attachment_texts[attachment_id] = result.text
        self._session_manager.update_session(session)
        return attachment

    def _find_attachment(self, session: Session, attachment_id: str) -> AttachmentMetadata:
        for attachment in session.attachments:
            if attachment.id == attachment_id:
                return attachment
        raise AttachmentError(f"attachment not found: {attachment_id}")

    @staticmethod
    def _guess_mime_type(path: Path) -> str:
        mime, _ = mimetypes.guess_type(path.name)
        if mime:
            return mime
        if path.suffix.lower() in {".md", ".markdown"}:
            return "text/markdown"
        return "application/octet-stream"

    @staticmethod
    def _generate_id() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def _delete_stored_file(path_str: str) -> None:
        try:
            path = Path(path_str)
        except Exception:
            return
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass


