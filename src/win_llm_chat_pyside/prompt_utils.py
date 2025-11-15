"""
プロンプトテンプレート適用時の共通ユーティリティ。
"""

from __future__ import annotations


def merge_template_text(existing_text: str, template_body: str) -> str:
    """
    入力欄にテンプレートを適用する際の結合ルール。

    - 既存の入力が空/空白のみならテンプレート本文で置き換える。
    - 既存の入力がある場合は末尾の空白を削ぎ、空行を挟んでテンプレート本文を追記する。
    - テンプレート本文が空の場合は既存の入力を返す。
    """
    existing = existing_text.strip()
    body = template_body.strip()
    if not body:
        return existing
    if not existing:
        return body
    return f"{existing}\n\n{body}"


