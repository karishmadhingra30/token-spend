import cost
from cost import TokenUsage, calculate_cost_parts, calculate_estimates, calculate_token_usage


def fake_count(messages, provider, model=None):
    return sum(len(message["content"].split()) for message in messages)


def test_simple_one_turn_cost(monkeypatch):
    monkeypatch.setattr(cost, "count_message_tokens", fake_count)
    rows, skipped = calculate_estimates(
        messages=[
            {"role": "user", "content": "hello there"},
            {"role": "assistant", "content": "hi friend"},
        ],
        selected_model_ids=["openai_gpt_4o"],
        monthly_volume=1000,
        full_context_per_turn=False,
    )

    assert skipped == []
    assert rows[0]["Input tokens/conv"] == 2
    assert rows[0]["Output tokens/conv"] == 2
    assert rows[0]["Monthly cost"] > 0


def test_full_context_increases_input_tokens(monkeypatch):
    monkeypatch.setattr(cost, "count_message_tokens", fake_count)
    messages = [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
        {"role": "user", "content": "three"},
        {"role": "assistant", "content": "four"},
    ]

    no_context = calculate_token_usage(messages, "openai", full_context_per_turn=False)
    full_context = calculate_token_usage(messages, "openai", full_context_per_turn=True)

    assert full_context.input_tokens > no_context.input_tokens
    assert full_context.output_tokens == no_context.output_tokens


def test_prompt_caching_discounts_only_repeated_input():
    usage = TokenUsage(input_tokens=1000, output_tokens=100, repeated_input_tokens=500)

    uncached = calculate_cost_parts(usage, 10, 20, "Anthropic direct API", False)
    cached = calculate_cost_parts(usage, 10, 20, "Anthropic direct API", True)

    assert cached["input_cost"] < uncached["input_cost"]
    assert cached["output_cost"] == uncached["output_cost"]


def test_none_pricing_skips_model():
    rows, skipped = calculate_estimates(
        messages=[{"role": "user", "content": "hello"}],
        selected_model_ids=["openai_gpt_5"],
        monthly_volume=1000,
    )

    assert rows == []
    assert "price not configured" in skipped[0]
