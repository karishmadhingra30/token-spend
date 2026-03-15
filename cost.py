"""Cost calculation logic for conversation estimates."""

from __future__ import annotations

from dataclasses import dataclass

from pricing import MODELS, is_price_configured
from tokenizer import count_message_tokens

INPUT_ROLES = {"system", "user"}


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    repeated_input_tokens: int = 0


def calculate_estimates(
    messages: list[dict[str, str]],
    selected_model_ids: list[str],
    monthly_volume: int,
    average_turns: int | None = None,
    full_context_per_turn: bool = True,
    apply_prompt_caching: bool = False,
) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    skipped: list[str] = []

    for model_id in selected_model_ids:
        model = MODELS.get(model_id)
        if model is None:
            skipped.append(f"{model_id}: model not found.")
            continue
        if not is_price_configured(model):
            skipped.append(
                f"{model['provider']} - {model['model_name']}: price not configured. {model.get('note', '')}".strip()
            )
            continue

        usage = calculate_token_usage(
            messages=messages,
            tokenizer_provider=model["tokenizer_provider"],
            tokenizer_model=model.get("tokenizer_model"),
            average_turns=average_turns,
            full_context_per_turn=full_context_per_turn,
        )
        cost_parts = calculate_cost_parts(
            usage=usage,
            input_price_per_million=float(model["input_price_per_million"]),
            output_price_per_million=float(model["output_price_per_million"]),
            provider=model["provider"],
            apply_prompt_caching=apply_prompt_caching,
        )

        rows.append(
            {
                "Provider": model["provider"],
                "Model": model["model_name"],
                "Input tokens/conv": usage.input_tokens,
                "Output tokens/conv": usage.output_tokens,
                "Input cost": cost_parts["input_cost"],
                "Output cost": cost_parts["output_cost"],
                "Monthly cost": cost_parts["per_conversation_cost"] * monthly_volume,
                "Per conversation cost": cost_parts["per_conversation_cost"],
                "Note": model.get("note", ""),
            }
        )

    rows.sort(key=lambda row: row["Monthly cost"])
    return rows, skipped


def calculate_token_usage(
    messages: list[dict[str, str]],
    tokenizer_provider: str,
    tokenizer_model: str | None = None,
    average_turns: int | None = None,
    full_context_per_turn: bool = True,
) -> TokenUsage:
    scaled_messages = _scale_messages_to_turns(messages, average_turns)
    if not full_context_per_turn:
        return TokenUsage(
            input_tokens=sum(
                count_message_tokens([message], tokenizer_provider, tokenizer_model)
                for message in scaled_messages
                if message["role"] in INPUT_ROLES
            ),
            output_tokens=sum(
                count_message_tokens([message], tokenizer_provider, tokenizer_model)
                for message in scaled_messages
                if message["role"] == "assistant"
            ),
            repeated_input_tokens=0,
        )

    input_tokens = 0
    output_tokens = 0
    repeated_input_tokens = 0
    previous_prompt_tokens = 0

    for index, message in enumerate(scaled_messages):
        if message["role"] == "assistant":
            request_input_messages = scaled_messages[:index]
            request_input = count_message_tokens(
                request_input_messages, tokenizer_provider, tokenizer_model
            )
            response_output = count_message_tokens([message], tokenizer_provider, tokenizer_model)
            input_tokens += request_input
            output_tokens += response_output
            repeated_input_tokens += min(previous_prompt_tokens, request_input)
            previous_prompt_tokens = request_input

    if output_tokens == 0:
        input_tokens = count_message_tokens(scaled_messages, tokenizer_provider, tokenizer_model)
        repeated_input_tokens = 0

    return TokenUsage(input_tokens, output_tokens, repeated_input_tokens)


def calculate_cost_parts(
    usage: TokenUsage,
    input_price_per_million: float,
    output_price_per_million: float,
    provider: str,
    apply_prompt_caching: bool = False,
) -> dict[str, float]:
    discount = _cache_discount(provider) if apply_prompt_caching else 0.0
    cached_tokens = min(usage.repeated_input_tokens, usage.input_tokens)
    full_price_input_tokens = usage.input_tokens - cached_tokens
    discounted_input_tokens = cached_tokens * (1 - discount)

    input_cost = (
        (full_price_input_tokens + discounted_input_tokens) * input_price_per_million
    ) / 1_000_000
    output_cost = (usage.output_tokens * output_price_per_million) / 1_000_000
    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "per_conversation_cost": input_cost + output_cost,
    }


def _cache_discount(provider: str) -> float:
    if provider in {"Anthropic direct API", "AWS Bedrock"}:
        return 0.90
    if provider == "OpenAI":
        return 0.50
    return 0.0


def _scale_messages_to_turns(
    messages: list[dict[str, str]],
    average_turns: int | None,
) -> list[dict[str, str]]:
    if not messages or not average_turns:
        return messages

    conversational = [message for message in messages if message["role"] in {"user", "assistant"}]
    sample_turns = len(conversational)
    if sample_turns == 0 or average_turns == sample_turns:
        return messages

    system_messages = [message for message in messages if message["role"] == "system"]
    if average_turns < sample_turns:
        keep = average_turns
        trimmed: list[dict[str, str]] = []
        seen = 0
        for message in messages:
            if message["role"] == "system":
                trimmed.append(message)
            elif seen < keep:
                trimmed.append(message)
                seen += 1
        return trimmed

    repeats = average_turns // sample_turns
    remainder = average_turns % sample_turns
    scaled = list(system_messages)
    body = conversational * repeats + conversational[:remainder]
    scaled.extend(body)
    return scaled
