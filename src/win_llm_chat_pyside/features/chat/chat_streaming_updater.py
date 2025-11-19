"""Handle streaming updates for ChatRichTextView."""

from __future__ import annotations

from typing import Optional

from win_llm_chat_pyside.features.chat.chat_rich_text_view import ChatRichTextView


class ChatStreamingUpdater:
    """Keeps the chat view in sync with streaming assistant responses."""

    def __init__(self, view: ChatRichTextView) -> None:
        self._view = view
        self._active_index: Optional[int] = None

    @property
    def active_index(self) -> Optional[int]:
        return self._active_index

    def begin(self, *, message_index: int) -> None:
        self._active_index = message_index

    def update_text(self, full_text: str) -> None:
        if self._active_index is None:
            return
        self._view.replace_message_content(self._active_index, full_text)

    def finalize(self) -> None:
        self._active_index = None

    def cancel(self) -> None:
        self._active_index = None

