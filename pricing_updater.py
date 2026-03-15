"""Manual pricing updater for pricing.py.

Run this script when you want to refresh configured prices from official
provider pages. It updates only prices it can parse confidently and leaves
uncertain models unchanged.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from pricing import MODELS, SOURCE_LINKS

PRICING_PATH = Path(__file__).with_name("pricing.py")


@dataclass(frozen=True)
class PriceUpdate:
    model_id: str
    input_price: float
    output_price: float
    source_label: str


@dataclass(frozen=True)
class UpdateResult:
    updates: list[PriceUpdate]
    skipped: list[str]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch official pricing pages and update configured prices in pricing.py."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print proposed updates without writing pricing.py.",
    )
    args = parser.parse_args()

    try:
        result = collect_updates()
    except Exception as exc:
        print(f"Pricing update failed: {exc}", file=sys.stderr)
        return 1

    if result.updates:
        for update in result.updates:
            model = MODELS[update.model_id]
            print(
                f"found {model['provider']} - {model['model_name']}: "
                f"input ${update.input_price:g}/M, output ${update.output_price:g}/M "
                f"from {update.source_label}"
            )
    else:
        print("No confident pricing updates found.")

    if result.skipped:
        print("\nSkipped:")
        for message in result.skipped:
            print(f"- {message}")

    if args.dry_run:
        print("\nDry run complete. pricing.py was not changed.")
        return 0

    if result.updates:
        update_pricing_file(PRICING_PATH, result.updates, dt.date.today().isoformat())
        print(f"\nUpdated {PRICING_PATH.name}. Run pytest before committing.")
    else:
        print("\nNo changes written.")
    return 0


def collect_updates() -> UpdateResult:
    pages = fetch_source_pages()
    updates: list[PriceUpdate] = []
    skipped: list[str] = []

    candidate_parsers = {
        "anthropic_claude_opus_4": (
            "Anthropic pricing",
            lambda text: parse_named_prices(text, ["Claude Opus 4", "Opus 4"]),
        ),
        "anthropic_claude_sonnet_4": (
            "Anthropic pricing",
            lambda text: parse_named_prices(text, ["Claude Sonnet 4", "Sonnet 4"]),
        ),
        "anthropic_claude_haiku_4": (
            "Anthropic pricing",
            lambda text: parse_named_prices(text, ["Claude Haiku 4", "Haiku 4"]),
        ),
        "openai_gpt_5": (
            "OpenAI pricing",
            lambda text: parse_named_prices(text, ["GPT-5", "gpt-5"]),
        ),
        "openai_gpt_5_mini": (
            "OpenAI pricing",
            lambda text: parse_named_prices(text, ["GPT-5 mini", "gpt-5-mini"]),
        ),
        "openai_gpt_4o": (
            "GPT-4o model pricing",
            lambda text: parse_named_prices(text, ["GPT-4o", "gpt-4o"]),
        ),
        "google_gemini_2_5_pro": (
            "Google Gemini pricing",
            lambda text: parse_named_prices(text, ["Gemini 2.5 Pro", "gemini-2.5-pro"]),
        ),
        "google_gemini_2_5_flash": (
            "Google Gemini pricing",
            lambda text: parse_named_prices(text, ["Gemini 2.5 Flash", "gemini-2.5-flash"]),
        ),
        "bedrock_claude_opus_4": (
            "AWS Bedrock pricing",
            lambda text: parse_named_prices(text, ["Claude Opus 4", "Opus 4"]),
        ),
        "bedrock_claude_sonnet_4": (
            "AWS Bedrock pricing",
            lambda text: parse_named_prices(text, ["Claude Sonnet 4", "Sonnet 4"]),
        ),
        "bedrock_claude_haiku_4": (
            "AWS Bedrock pricing",
            lambda text: parse_named_prices(text, ["Claude Haiku 4", "Haiku 4"]),
        ),
    }

    for model_id, (source_label, parser) in candidate_parsers.items():
        page = pages.get(source_label)
        if not page:
            skipped.append(f"{MODELS[model_id]['model_name']}: source page unavailable.")
            continue

        parsed = parser(page)
        if parsed is None:
            skipped.append(
                f"{MODELS[model_id]['provider']} - {MODELS[model_id]['model_name']}: "
                "could not parse an exact input/output price pair."
            )
            continue

        input_price, output_price = parsed
        validation_error = validate_price_pair(model_id, input_price, output_price)
        if validation_error:
            skipped.append(
                f"{MODELS[model_id]['provider']} - {MODELS[model_id]['model_name']}: "
                f"{validation_error}"
            )
            continue
        updates.append(PriceUpdate(model_id, input_price, output_price, source_label))

    return UpdateResult(updates=updates, skipped=skipped)


def fetch_source_pages() -> dict[str, str]:
    pages: dict[str, str] = {}
    for label, url in SOURCE_LINKS.items():
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 pricing-updater/1.0 "
                    "(manual LLM cost estimator maintenance)"
                )
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except Exception as exc:
            print(f"warning: failed to fetch {label}: {exc}", file=sys.stderr)
            continue
        pages[label] = normalize_page_text(raw)
    return pages


def normalize_page_text(raw: str) -> str:
    text = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", " ", raw, flags=re.I)
    text = re.sub(r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text)


def parse_named_prices(text: str, names: list[str]) -> tuple[float, float] | None:
    for name in names:
        match = find_price_window(text, name)
        if not match:
            continue
        parsed = parse_input_output_labeled_prices(match)
        if parsed is not None:
            return parsed
    return None


def find_price_window(text: str, name: str) -> str | None:
    pattern = re.compile(rf"(?<![\w.-]){re.escape(name)}(?![\w.-])", re.I)
    match = pattern.search(text)
    if not match:
        return None
    return text[match.start() : match.start() + 900]


def extract_dollar_prices(text: str) -> list[float]:
    prices: list[float] = []
    for raw in re.findall(r"\$\s*([0-9]+(?:\.[0-9]+)?)", text):
        value = float(raw)
        if 0 < value <= 500:
            prices.append(value)
    return prices


def parse_input_output_labeled_prices(text: str) -> tuple[float, float] | None:
    input_match = re.search(r"\binput\b[^$]{0,180}\$\s*([0-9]+(?:\.[0-9]+)?)", text, re.I)
    output_match = re.search(r"\boutput\b[^$]{0,220}\$\s*([0-9]+(?:\.[0-9]+)?)", text, re.I)
    if input_match and output_match:
        return float(input_match.group(1)), float(output_match.group(1))

    prices = extract_dollar_prices(text)
    if len(prices) == 2:
        return prices[0], prices[1]
    return None


def validate_price_pair(model_id: str, input_price: float, output_price: float) -> str | None:
    if input_price <= 0 or output_price <= 0:
        return "parsed non-positive pricing; skipped."
    if output_price < input_price:
        return (
            f"parsed output price ${output_price:g}/M is below input price "
            f"${input_price:g}/M; skipped as suspicious."
        )

    model = MODELS[model_id]
    current_input = model.get("input_price_per_million")
    current_output = model.get("output_price_per_million")
    if current_input is not None and current_output is not None:
        if not is_within_review_band(input_price, float(current_input)):
            return (
                f"parsed input price ${input_price:g}/M differs too much from "
                f"current ${float(current_input):g}/M; review manually."
            )
        if not is_within_review_band(output_price, float(current_output)):
            return (
                f"parsed output price ${output_price:g}/M differs too much from "
                f"current ${float(current_output):g}/M; review manually."
            )

    return None


def is_within_review_band(parsed: float, current: float) -> bool:
    lower = current * 0.75
    upper = current * 1.25
    return lower <= parsed <= upper


def update_pricing_file(path: Path, updates: list[PriceUpdate], updated_date: str) -> None:
    source = path.read_text()
    source = re.sub(
        r'PRICING_LAST_UPDATED = "[^"]+"',
        f'PRICING_LAST_UPDATED = "{updated_date}"',
        source,
    )
    source = re.sub(
        r"Pricing last updated: \d{4}-\d{2}-\d{2}\.",
        f"Pricing last updated: {updated_date}.",
        source,
    )

    for update in updates:
        source = replace_model_price(
            source,
            update.model_id,
            "input_price_per_million",
            update.input_price,
        )
        source = replace_model_price(
            source,
            update.model_id,
            "output_price_per_million",
            update.output_price,
        )

    path.write_text(source)


def replace_model_price(source: str, model_id: str, key: str, value: float) -> str:
    block_pattern = re.compile(
        rf'("{re.escape(model_id)}":\s*\{{.*?^\s*\}},)',
        re.M | re.S,
    )
    match = block_pattern.search(source)
    if not match:
        raise ValueError(f"Could not find model block for {model_id}")

    block = match.group(1)
    key_pattern = re.compile(rf'("{re.escape(key)}":\s*)(None|[0-9]+(?:\.[0-9]+)?)')
    new_block, count = key_pattern.subn(rf"\g<1>{format_price(value)}", block, count=1)
    if count != 1:
        raise ValueError(f"Could not update {key} for {model_id}")

    return source[: match.start(1)] + new_block + source[match.end(1) :]


def format_price(value: float) -> str:
    if value.is_integer():
        return f"{value:.1f}"
    return f"{value:.4f}".rstrip("0").rstrip(".")


if __name__ == "__main__":
    raise SystemExit(main())
