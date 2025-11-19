from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from win_llm_chat_pyside.models import AttachmentMetadata, Session


@dataclass(frozen=True)
class AttachmentContextResult:
    text: str
    total_chars: int
    truncated: bool
    included_ids: list[str]
    skipped_ids: list[str]


class AttachmentContextBuilder:
    """選択された添付ファイルから LLM に渡すコンテキストを構築する。"""

    def __init__(self, *, default_max_chars: int = 20_000) -> None:
        self._default_max_chars = max(0, int(default_max_chars))

    def build(
        self,
        session: Session,
        attachment_ids: Sequence[str],
        *,
        max_chars: int | None = None,
    ) -> AttachmentContextResult:
        """選択された添付 ID 群からコンテキスト文字列を生成する。"""

        if not attachment_ids:
            return AttachmentContextResult("", 0, False, [], [])

        attachment_map = {meta.id: meta for meta in session.attachments}
        attachment_texts = session.attachment_texts or {}

        included_ids: list[str] = []
        skipped_ids: list[str] = []
        blocks: list[str] = []
        total_chars = 0

        for attachment_id in attachment_ids:
            metadata = attachment_map.get(attachment_id)
            if not metadata:
                skipped_ids.append(attachment_id)
                continue

            raw_text = (attachment_texts.get(attachment_id) or "").strip()
            if not raw_text:
                skipped_ids.append(attachment_id)
                continue

            block = self._render_block(metadata, raw_text)
            blocks.append(block)
            included_ids.append(attachment_id)
            total_chars += len(block)

        combined_text = self._join_blocks(blocks)
        limit = self._effective_max_chars(max_chars)
        truncated = False

        if limit is not None and len(combined_text) > limit:
            truncated = True
            combined_text = combined_text[:limit].rstrip()

        return AttachmentContextResult(
            text=combined_text,
            total_chars=total_chars,
            truncated=truncated,
            included_ids=included_ids,
            skipped_ids=skipped_ids,
        )

    def _effective_max_chars(self, override: int | None) -> int | None:
        if override is None:
            return self._default_max_chars or None
        if override <= 0:
            return None
        return override

    def _render_block(self, metadata: AttachmentMetadata, text: str) -> str:
        header_lines = [
            f"### 添付: {metadata.filename}",
            f"- 種別: {metadata.mime_type or '不明'}",
            f"- サイズ: {self._format_bytes(metadata.size_bytes)}",
        ]
        if metadata.page_count:
            header_lines.append(f"- ページ数: {metadata.page_count}")
        if metadata.length_warning:
            header_lines.append("- 注: 抽出テキストが長文です")
        header_lines.append("")
        header_lines.append(text.strip())
        return "\n".join(header_lines).strip()

    @staticmethod
    def _join_blocks(blocks: Iterable[str]) -> str:
        return "\n\n---\n\n".join(block for block in blocks if block).strip()

    @staticmethod
    def _format_bytes(size_bytes: int) -> str:
        if size_bytes < 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB"]
        size = float(size_bytes)
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        return f"{size:.1f} {units[unit_index]}"


