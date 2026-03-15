"""Conversation parsing for pasted JSON or plain dialogue."""

from __future__ import annotations

import json
import re
from typing import Any

VALID_ROLES = {"system", "user", "assistant"}
ROLE_ALIASES = {
    "human": "user",
    "customer": "user",
    "ai": "assistant",
    "bot": "assistant",
}
ROLE_LINE_RE = re.compile(r"^\s*(User|Assistant|System)\s*:\s*(.*)$", re.IGNORECASE)


def normalize_role(role: Any) -> str | None:
    normalized = str(role or "").strip().lower()
    normalized = ROLE_ALIASES.get(normalized, normalized)
    if normalized in VALID_ROLES:
        return normalized
    return None


def parse_conversation(text: str) -> list[dict[str, str]]:
    if not text or not text.strip():
        return []

    stripped = text.strip()
    if stripped.startswith("["):
        parsed = _parse_json_messages(stripped)
        if parsed:
            return parsed

    return _parse_dialogue(stripped)


def _parse_json_messages(text: str) -> list[dict[str, str]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []

    if not isinstance(payload, list):
        return []

    messages: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            return []
        role = normalize_role(item.get("role"))
        content = item.get("content")
        if role is None or content is None:
            return []
        messages.append({"role": role, "content": str(content).strip()})
    return [message for message in messages if message["content"]]


def _parse_dialogue(text: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    current: dict[str, str] | None = None

    for line in text.splitlines():
        match = ROLE_LINE_RE.match(line)
        if match:
            if current and current["content"].strip():
                current["content"] = current["content"].strip()
                messages.append(current)
            role = normalize_role(match.group(1))
            current = {"role": role or "user", "content": match.group(2).strip()}
            continue

        if current is not None:
            current["content"] = f"{current['content']}\n{line}".strip()

    if current and current["content"].strip():
        current["content"] = current["content"].strip()
        messages.append(current)

    return messages


def count_turns(messages: list[dict[str, str]]) -> int:
    return sum(1 for message in messages if message["role"] in {"user", "assistant"})
