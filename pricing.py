"""Pricing configuration for the LLM cost estimator.

Pricing last updated: 2026-05-26.

Official pricing pages:
- OpenAI: https://developers.openai.com/api/docs/pricing
- GPT-4o: https://developers.openai.com/api/docs/models/gpt-4o
- Anthropic: https://platform.claude.com/docs/en/about-claude/pricing
- AWS Bedrock: https://aws.amazon.com/bedrock/pricing/
- Google Gemini: https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing

Prices are USD per 1 million tokens. Leave uncertain prices as None so the
app skips those models instead of presenting guessed estimates.
"""

PRICING_LAST_UPDATED = "2026-05-26"

SOURCE_LINKS = {
    "OpenAI pricing": "https://developers.openai.com/api/docs/pricing",
    "GPT-4o model pricing": "https://developers.openai.com/api/docs/models/gpt-4o",
    "Anthropic pricing": "https://platform.claude.com/docs/en/about-claude/pricing",
    "AWS Bedrock pricing": "https://aws.amazon.com/bedrock/pricing/",
    "Google Gemini pricing": "https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing",
}

MODELS = {
    "bedrock_claude_opus_4": {
        "provider": "AWS Bedrock",
        "model_name": "Claude Opus 4",
        "tokenizer_provider": "anthropic",
        "tokenizer_model": "claude-opus-4-20250514",
        "input_price_per_million": None,
        "output_price_per_million": None,
        "context_window": 200_000,
        "note": "Exact current AWS Bedrock row not configured. Verify on AWS Bedrock pricing before use.",
    },
    "bedrock_claude_sonnet_4": {
        "provider": "AWS Bedrock",
        "model_name": "Claude Sonnet 4",
        "tokenizer_provider": "anthropic",
        "tokenizer_model": "claude-sonnet-4-20250514",
        "input_price_per_million": None,
        "output_price_per_million": None,
        "context_window": 200_000,
        "note": "Exact current AWS Bedrock row not configured. Verify on AWS Bedrock pricing before use.",
    },
    "bedrock_claude_haiku_4": {
        "provider": "AWS Bedrock",
        "model_name": "Claude Haiku 4",
        "tokenizer_provider": "anthropic",
        "tokenizer_model": "claude-haiku-4",
        "input_price_per_million": None,
        "output_price_per_million": None,
        "context_window": None,
        "note": "Exact Claude Haiku 4 price not configured. Current public docs list Haiku 4.5 rather than Haiku 4.",
    },
    "anthropic_claude_opus_4": {
        "provider": "Anthropic direct API",
        "model_name": "Claude Opus 4",
        "tokenizer_provider": "anthropic",
        "tokenizer_model": "claude-opus-4-20250514",
        "input_price_per_million": 15.0,
        "output_price_per_million": 75.0,
        "context_window": 200_000,
        "note": "Prompt caching cache hits are billed at 10% of base input price.",
    },
    "anthropic_claude_sonnet_4": {
        "provider": "Anthropic direct API",
        "model_name": "Claude Sonnet 4",
        "tokenizer_provider": "anthropic",
        "tokenizer_model": "claude-sonnet-4-20250514",
        "input_price_per_million": 3.0,
        "output_price_per_million": 15.0,
        "context_window": 200_000,
        "note": "Prompt caching cache hits are billed at 10% of base input price.",
    },
    "anthropic_claude_haiku_4": {
        "provider": "Anthropic direct API",
        "model_name": "Claude Haiku 4",
        "tokenizer_provider": "anthropic",
        "tokenizer_model": "claude-haiku-4",
        "input_price_per_million": None,
        "output_price_per_million": None,
        "context_window": None,
        "note": "Exact Claude Haiku 4 price not configured. Current public docs list Haiku 4.5 rather than Haiku 4.",
    },
    "openai_gpt_5": {
        "provider": "OpenAI",
        "model_name": "GPT-5",
        "tokenizer_provider": "openai",
        "tokenizer_model": "gpt-5",
        "input_price_per_million": None,
        "output_price_per_million": None,
        "context_window": None,
        "note": "Exact GPT-5 price not configured on the current official pricing page; verify before pitching.",
    },
    "openai_gpt_5_mini": {
        "provider": "OpenAI",
        "model_name": "GPT-5 mini",
        "tokenizer_provider": "openai",
        "tokenizer_model": "gpt-5-mini",
        "input_price_per_million": None,
        "output_price_per_million": None,
        "context_window": None,
        "note": "Exact GPT-5 mini price not configured on the current official pricing page; verify before pitching.",
    },
    "openai_gpt_4o": {
        "provider": "OpenAI",
        "model_name": "GPT-4o",
        "tokenizer_provider": "openai",
        "tokenizer_model": "gpt-4o",
        "input_price_per_million": 2.5,
        "output_price_per_million": 10.0,
        "context_window": 128_000,
        "note": "Cached input price is 50% of base input price.",
    },
    "google_gemini_2_5_pro": {
        "provider": "Google Gemini",
        "model_name": "Gemini 2.5 Pro",
        "tokenizer_provider": "gemini",
        "tokenizer_model": "gemini-2.5-pro",
        "input_price_per_million": 2.25,
        "output_price_per_million": 18.0,
        "context_window": 1_000_000,
        "note": "Standard text pricing for prompts up to 200K input tokens; higher tiers may apply beyond that.",
    },
    "google_gemini_2_5_flash": {
        "provider": "Google Gemini",
        "model_name": "Gemini 2.5 Flash",
        "tokenizer_provider": "gemini",
        "tokenizer_model": "gemini-2.5-flash",
        "input_price_per_million": 0.3,
        "output_price_per_million": 2.5,
        "context_window": 1_000_000,
        "note": "Standard text, image, and video input pricing; this app estimates text-only conversations.",
    },
}

DEFAULT_MODEL_IDS = [
    "anthropic_claude_sonnet_4",
    "openai_gpt_4o",
    "google_gemini_2_5_flash",
]


def is_price_configured(model: dict) -> bool:
    return (
        model.get("input_price_per_million") is not None
        and model.get("output_price_per_million") is not None
    )


def model_label(model_id: str) -> str:
    model = MODELS[model_id]
    return f"{model['provider']} - {model['model_name']}"
