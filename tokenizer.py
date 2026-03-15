"""Provider-specific token counting with graceful offline fallbacks."""

from __future__ import annotations

import math
import os
from functools import lru_cache


def heuristic_token_count(text: str) -> int:
    return max(1, math.ceil(len(text or "") / 4))


def count_text_tokens(text: str, provider: str, model: str | None = None) -> int:
    if provider == "openai":
        return _count_openai_tokens(text, model)
    if provider in {"anthropic", "gemini"}:
        return heuristic_token_count(text)
    return heuristic_token_count(text)


def count_message_tokens(
    messages: list[dict[str, str]],
    provider: str,
    model: str | None = None,
) -> int:
    if not messages:
        return 0

    if provider == "anthropic":
        count = _count_anthropic_messages(messages, model)
        if count is not None:
            return count
    if provider == "gemini":
        count = _count_gemini_messages(messages, model)
        if count is not None:
            return count

    return sum(
        count_text_tokens(f"{message['role']}: {message['content']}", provider, model)
        for message in messages
    )


def count_tokens_by_role(
    messages: list[dict[str, str]],
    provider: str,
    model: str | None = None,
) -> dict[str, int]:
    totals = {"system": 0, "user": 0, "assistant": 0}
    for message in messages:
        role = message["role"]
        totals[role] = totals.get(role, 0) + count_message_tokens([message], provider, model)
    return totals


def _count_openai_tokens(text: str, model: str | None) -> int:
    try:
        import tiktoken

        try:
            encoding = tiktoken.encoding_for_model(model or "gpt-4o")
        except KeyError:
            encoding = tiktoken.get_encoding("o200k_base")
        return len(encoding.encode(text or ""))
    except Exception:
        return heuristic_token_count(text)


def _count_anthropic_messages(messages: list[dict[str, str]], model: str | None) -> int | None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic

        system_text = "\n\n".join(
            message["content"] for message in messages if message["role"] == "system"
        )
        api_messages = [
            {"role": message["role"], "content": message["content"]}
            for message in messages
            if message["role"] in {"user", "assistant"}
        ]
        if not api_messages:
            return heuristic_token_count(system_text)

        client = _anthropic_client()
        kwargs = {"model": model or "claude-sonnet-4-20250514", "messages": api_messages}
        if system_text:
            kwargs["system"] = system_text
        response = client.messages.count_tokens(**kwargs)
        return int(response.input_tokens)
    except Exception:
        return None


@lru_cache(maxsize=1)
def _anthropic_client():
    import anthropic

    return anthropic.Anthropic()


def _count_gemini_messages(messages: list[dict[str, str]], model: str | None) -> int | None:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel(model or "gemini-2.5-flash")
        prompt = "\n\n".join(f"{message['role']}: {message['content']}" for message in messages)
        response = gemini_model.count_tokens(prompt)
        return int(response.total_tokens)
    except Exception:
        return None
