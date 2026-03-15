from pathlib import Path

from pricing_updater import (
    PriceUpdate,
    is_within_review_band,
    parse_input_output_labeled_prices,
    update_pricing_file,
)


def test_parse_labeled_prices():
    assert parse_input_output_labeled_prices("GPT-4o Input $2.50 Output $10.00") == (
        2.5,
        10.0,
    )


def test_review_band_is_conservative():
    assert is_within_review_band(10, 10)
    assert is_within_review_band(12.5, 10)
    assert not is_within_review_band(13, 10)


def test_update_pricing_file_updates_date_and_model_prices(tmp_path):
    pricing_file = tmp_path / "pricing.py"
    pricing_file.write_text(
        '''"""Pricing last updated: 2026-01-01."""

PRICING_LAST_UPDATED = "2026-01-01"

MODELS = {
    "openai_gpt_4o": {
        "input_price_per_million": 2.5,
        "output_price_per_million": 10.0,
    },
}
'''
    )

    update_pricing_file(
        Path(pricing_file),
        [PriceUpdate("openai_gpt_4o", 3.0, 11.0, "test")],
        "2026-05-26",
    )

    updated = pricing_file.read_text()
    assert 'PRICING_LAST_UPDATED = "2026-05-26"' in updated
    assert "Pricing last updated: 2026-05-26." in updated
    assert '"input_price_per_million": 3.0' in updated
    assert '"output_price_per_million": 11.0' in updated
