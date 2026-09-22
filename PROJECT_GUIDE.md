# Multi-provider LLM cost estimator

A browser-based planning tool for teams comparing the cost of an AI workflow before they commit to a provider, model, or monthly volume.

## What it does

Visitors paste a representative support or product conversation, select configured models, and set projected volume. The app parses the exchange, estimates per-conversation and monthly spend, and visualizes the result at several scales.

Provider keys are optional. Without them, Anthropic and Gemini token counts use a disclosed character-based approximation so the public demo remains usable without exposing credentials.

## Architecture

```text
Browser input
    -> Streamlit UI (app.py)
    -> parser.py + tokenizer.py
    -> cost.py + versioned pricing.py
    -> comparison tables and Plotly charts
```

- `app.py`: collects the workflow inputs and renders the demo.
- `parser.py` and `tokenizer.py`: turn a pasted conversation into role-aware token estimates.
- `cost.py`: applies provider pricing, context growth, caching, and volume assumptions.
- `pricing.py`: versioned, reviewable model prices and source links.

## Stack

| Layer | Technology | Why it is here |
| --- | --- | --- |
| UI | Streamlit | Fast, interactive Python interface for a self-serve demo. |
| Analysis | Python, pandas | Parses conversations and calculates cost scenarios. |
| Charts | Plotly | Makes provider and scale tradeoffs legible. |
| Token counting | tiktoken and optional provider SDKs | Uses local or provider-aware counts when available. |

## Running it

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Run the automated checks with `pytest`. The test suite passed locally on 2026-09-22.

For a public Streamlit deployment, use `app.py` as the entry point and leave `ALLOW_PRICING_UPDATE` unset. This keeps the demo read-only; price refreshes should be reviewed and committed through Git.

## Decisions and tradeoffs

| Decision | Chosen | Rejected or alternative | Why / tradeoff |
| --- | --- | --- | --- |
| Public demo behavior | Read-only pricing | Let visitors trigger the updater | Prevents public traffic from changing the deployed server's price configuration. |
| Pricing source | Versioned Python configuration | Live provider-price fetches at page load | Makes assumptions auditable and avoids presenting unreviewed current prices as fact. |
| Missing provider keys | Explicit heuristic fallback | Require API keys | Lets recruiters and customers try the demo without credentials, at the cost of less precise token counts for some providers. |
