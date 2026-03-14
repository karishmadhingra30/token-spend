# Multi-provider LLM cost estimator

A Streamlit app for estimating monthly AI project costs across OpenAI, Anthropic, AWS Bedrock, and Google Gemini models.

![Screenshot placeholder](docs/screenshot-placeholder.png)

## What it does

This tool is built for early internal AI project planning. Paste in a representative multi-turn conversation, choose the models you want to compare, set expected monthly volume, and get:

- a screenshot-friendly monthly cost comparison chart
- a detailed per-model cost breakdown
- a volume sensitivity chart from 100 to 100,000 conversations per month
- parsed message and token sanity checks before estimating

The estimator supports two paste formats:

- Plain dialogue: lines beginning with `System:`, `User:`, or `Assistant:`
- JSON: a list of `{"role": "...", "content": "..."}` message objects

## Tech stack

- Python 3.10+
- Streamlit for the UI
- Plotly for charts
- pandas for the breakdown table
- tiktoken for OpenAI token counting
- Anthropic Python SDK for Claude token counting when `ANTHROPIC_API_KEY` is configured
- google-generativeai for Gemini token counting when `GOOGLE_API_KEY` is configured
- pytest for parser and cost calculation tests

No database is used. Pricing is stored in `pricing.py` so it is easy to audit and update.

## Project structure

```text
.
├── app.py              # Streamlit UI
├── pricing.py          # Model pricing config, source links, and last-updated date
├── pricing_updater.py  # Manual script for refreshing configured prices
├── tokenizer.py        # Provider-specific token counting with heuristic fallbacks
├── cost.py             # Cost calculation and prompt-caching math
├── parser.py           # Dialogue and JSON conversation parsing
├── requirements.txt
├── tests/
│   ├── test_cost.py
│   └── test_parser.py
├── README.md
└── .env.example
```

## Install and run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL printed by Streamlit, usually:

```text
http://localhost:8501
```

API keys are optional:

```bash
export ANTHROPIC_API_KEY=...
export GOOGLE_API_KEY=...
```

`OPENAI_API_KEY` is listed in `.env.example` for completeness, but OpenAI token counting uses `tiktoken` locally and does not require a key.

## Pricing disclaimer

Pricing is configured as of 2026-05-26. Verify provider pricing before pitching or budgeting.

Pricing changes often. Any model with uncertain pricing is intentionally set to `None` in `pricing.py`, and the app skips that model with a clear "price not configured" message instead of guessing.

Token counts for Gemini and Anthropic use provider token counters when API keys are configured. Without those keys, the app falls back to an approximate `ceil(characters / 4)` heuristic.

## How pricing updates work

The app does not automatically pull live pricing at runtime. Prices are static configuration in `pricing.py` by design, because provider pricing pages change structure and sometimes include tiers, regional multipliers, caching rates, and batch discounts that should be reviewed before being used in a budget.

For a manual refresh, run the updater:

```bash
python pricing_updater.py --dry-run
python pricing_updater.py
pytest
```

You can also click **Update pricing** in the app sidebar. The button runs `pricing_updater.py`, prints the updater output in the UI, and reloads the pricing configuration for the current session.

`pricing_updater.py` fetches the official source pages in `SOURCE_LINKS`, updates only exact input/output price pairs it can parse confidently, and leaves uncertain models unchanged. It also updates `PRICING_LAST_UPDATED` when it writes changes.

Manual review is still required after running the updater. If provider pages change format or list tiered pricing, the script may skip a model rather than risk writing a guessed price.

You can also update prices by hand:

1. Edit `PRICING_LAST_UPDATED`.
2. Check the official source links in `SOURCE_LINKS`.
3. Update `MODELS` prices in USD per 1 million input and output tokens.
4. Leave uncertain prices as `None`.
5. Run `pytest`.

## Design decisions, learnings, and pivots

- Full-context-per-turn estimation is enabled by default because production chat apps usually resend prior conversation context on each turn. This often changes the estimate dramatically compared with counting the pasted transcript once.
- Prompt caching is modeled only against repeated input tokens. Anthropic and AWS Claude models use a 90% repeated-input discount, OpenAI uses a 50% repeated-input discount, and Gemini is left undiscounted unless configured later.
- Exact requested model names are preserved in the UI even when current provider docs have moved on to newer aliases or versions.
- Conservative pricing is better than impressive-looking precision. GPT-5, GPT-5 mini, Claude Haiku 4, and AWS Bedrock Claude entries are present but skipped unless exact prices are configured.
- Token preview uses the same provider-specific counting path as the estimate so users do not see one number in the sanity check and another in the cost calculation.
- The first version keeps pricing in Python rather than YAML or a database to make updates straightforward and reviewable in code review.
- Pricing refresh is a manual maintenance step, not a hidden runtime dependency, so users can review diffs before relying on new estimates.

## Tests

Run:

```bash
pytest
```

Current tests cover:

- JSON conversation parsing
- plain dialogue parsing with continuation lines
- role normalization
- invalid input handling
- full-context token growth
- prompt-caching cost reduction
- graceful skipping for unconfigured prices
- pricing updater parsing, conservative review-band checks, and file rewrites
