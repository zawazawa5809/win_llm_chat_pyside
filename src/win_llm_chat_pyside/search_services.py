"""検索ロジックを集約したサービス群。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from .models import Message, SessionSummary


@dataclass
class SessionHit:
    """セッション内検索の一致結果。"""

    message_index: int
    start: int
    length: int


@dataclass
class AttachmentSearchInput:
    """添付テキスト検索の入力。"""

    attachment_id: str
    filename: str
    text: str


@dataclass
class AttachmentHit:
    """添付テキスト検索の結果。"""

    attachment_id: str
    filename: str
    snippet: str
    hit_count: int


class SessionSearchService:
    """セッション内／セッション一覧検索ロジックを提供する。"""

    def __init__(self, *, min_keyword_length: int = 2) -> None:
        self._min_keyword_length = max(1, min_keyword_length)

    @property
    def min_keyword_length(self) -> int:
        return self._min_keyword_length

    def normalize_keyword(self, keyword: str | None) -> str:
        return (keyword or "").strip()

    def is_valid_keyword(self, keyword: str | None) -> bool:
        normalized = self.normalize_keyword(keyword)
        return len(normalized) >= self._min_keyword_length

    def search_in_session(self, messages: Sequence[Message], keyword: str) -> List[SessionHit]:
        normalized = self.normalize_keyword(keyword)
        if len(normalized) < self._min_keyword_length:
            return []
        lower_keyword = normalized.casefold()
        hits: list[SessionHit] = []
        for index, message in enumerate(messages):
            content = message.content or ""
            lower_text = content.casefold()
            start = 0
            while True:
                found = lower_text.find(lower_keyword, start)
                if found == -1:
                    break
                hits.append(SessionHit(message_index=index, start=found, length=len(lower_keyword)))
                start = found + len(lower_keyword)
        return hits

    def search_in_summaries(self, summaries: Iterable[SessionSummary], keyword: str) -> List[str]:
        normalized = self.normalize_keyword(keyword)
        if len(normalized) < self._min_keyword_length:
            return []
        lower_keyword = normalized.casefold()
        matched_ids: list[str] = []
        for summary in summaries:
            haystack = f"{summary.name}\n{summary.preview_text}".casefold()
            if lower_keyword in haystack:
                matched_ids.append(summary.id)
        return matched_ids


class AttachmentSearchService:
    """添付テキスト内のキーワードハイライトと抜粋生成を担当する。"""

    def __init__(
        self,
        *,
        min_keyword_length: int = 2,
        context_chars: int = 80,
        max_snippet_length: int = 240,
    ) -> None:
        self._min_keyword_length = max(1, min_keyword_length)
        self._context_chars = max(20, context_chars)
        self._max_snippet_length = max(60, max_snippet_length)

    def normalize_keyword(self, keyword: str | None) -> str:
        return (keyword or "").strip()

    def is_valid_keyword(self, keyword: str | None) -> bool:
        normalized = self.normalize_keyword(keyword)
        return len(normalized) >= self._min_keyword_length

    def search_in_attachments(
        self,
        attachments: Sequence[AttachmentSearchInput],
        keyword: str,
    ) -> List[AttachmentHit]:
        normalized = self.normalize_keyword(keyword)
        if len(normalized) < self._min_keyword_length:
            return []
        lower_keyword = normalized.casefold()
        hits: list[AttachmentHit] = []
        for attachment in attachments:
            filename = attachment.filename or ""
            text = attachment.text or ""
            lower_text = text.casefold()
            lower_filename = filename.casefold()

            start = 0
            hit_positions: list[int] = []
            while True:
                found = lower_text.find(lower_keyword, start)
                if found == -1:
                    break
                hit_positions.append(found)
                start = found + len(lower_keyword)

            filename_match = lower_keyword in lower_filename
            if not filename_match and not hit_positions:
                continue

            if hit_positions:
                snippet = self._build_snippet(text, hit_positions[0], len(lower_keyword))
                hit_count = len(hit_positions)
            else:
                snippet = "[ファイル名に一致]"
                hit_count = 1

            hits.append(
                AttachmentHit(
                    attachment_id=attachment.attachment_id,
                    filename=filename,
                    snippet=snippet,
                    hit_count=hit_count,
                )
            )
        return hits

    def _build_snippet(self, text: str, match_index: int, match_length: int) -> str:
        start = max(0, match_index - self._context_chars)
        end = min(len(text), match_index + match_length + self._context_chars)
        snippet = text[start:end].strip()
        snippet = re.sub(r"\s+", " ", snippet)
        if len(snippet) > self._max_snippet_length:
            snippet = snippet[: self._max_snippet_length].rstrip() + "…"
        prefix = "…" if start > 0 else ""
        suffix = "…" if end < len(text) else ""
        return f"{prefix}{snippet}{suffix}"


