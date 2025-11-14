"""
LlmClient の生成を担当するファクトリ。
"""

from typing import Optional, Tuple

from .client import OpenAiCompatibleClient, OllamaClient, BaseLlmClient
from .config import Profile


def create_llm_client(
    profile: Profile,
    connect_timeout_ms: int,
    total_timeout_ms: int,
) -> BaseLlmClient:  # type: ignore[type-arg]
    """
    プロファイルに基づいて LLM クライアントを生成する。
    """
    connect_s = max(0.1, connect_timeout_ms / 1000.0)
    read_s = max(0.1, total_timeout_ms / 1000.0)
    timeout: float | Tuple[float, float] = (connect_s, read_s)

    if profile.type == "ollama":
        # OllamaClient は timeout を秒（readベース）で受ける実装
        return OllamaClient(
            base_url=profile.base_url,
            model=profile.model,
            timeout=int(read_s),
        )

    # 既定は OpenAI 互換として生成
    return OpenAiCompatibleClient(
        base_url=profile.base_url,
        model=profile.model,
        api_key=profile.api_key,
        timeout=timeout,
    )


