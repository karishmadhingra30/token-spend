from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import cost as cost_calculator
import pricing as pricing_config
from parser import count_turns, parse_conversation
from tokenizer import count_tokens_by_role

SAMPLE_CONVERSATION = """System: You are a helpful internal assistant.
User: Can you summarize this support ticket?
Assistant: Sure. Paste the ticket and I will summarize the issue, impact, and next step.
User: The customer cannot access their dashboard after SSO login.
Assistant: The customer is blocked after SSO login. The next step is to inspect the SAML assertion and dashboard authorization logs."""

PROVIDER_COLORS = {
    "AWS Bedrock": "#8C4A2F",
    "Anthropic direct API": "#2F6F73",
    "OpenAI": "#3B6EA8",
    "Google Gemini": "#7A5C99",
}


def main() -> None:
    st.set_page_config(page_title="LLM Cost Estimator", layout="wide")
    st.title("Multi-provider LLM cost estimator")

    with st.sidebar:
        if st.button("Update pricing", use_container_width=True):
            run_pricing_updater()
        st.info(
            f"Pricing last updated: {pricing_config.PRICING_LAST_UPDATED}. Verify before pitching."
        )
        st.caption("Pricing sources")
        for label, url in pricing_config.SOURCE_LINKS.items():
            st.markdown(f"- [{label}]({url})")

    conversation_text = st.text_area(
        "Sample multi-turn conversation",
        value=SAMPLE_CONVERSATION,
        height=240,
        help="Paste JSON messages or lines starting with User:, Assistant:, or System:.",
    )
    messages = parse_conversation(conversation_text)

    if not messages:
        st.warning("Paste a JSON message list or plain dialogue to estimate costs.")
        return

    sample_turn_count = count_turns(messages)
    total_chars = sum(len(message["content"]) for message in messages)

    metric_cols = st.columns(2)
    metric_cols[0].metric("Parsed turns", sample_turn_count)
    metric_cols[1].metric("Characters", f"{total_chars:,}")

    controls = st.columns([1, 1, 2])
    monthly_volume = controls[0].number_input(
        "Monthly conversation volume",
        min_value=1,
        value=1_000,
        step=100,
    )
    average_turns = controls[1].number_input(
        "Average turns per conversation",
        min_value=1,
        value=max(1, sample_turn_count),
        step=1,
    )
    selected_labels = controls[2].multiselect(
        "Provider/model selection",
        options=list(pricing_config.MODELS.keys()),
        default=[
            model_id
            for model_id in pricing_config.DEFAULT_MODEL_IDS
            if model_id in pricing_config.MODELS
        ],
        format_func=pricing_config.model_label,
    )

    with st.expander("Advanced", expanded=False):
        full_context_per_turn = st.toggle(
            "Assume each turn includes full prior conversation context",
            value=True,
            help="Most chat apps resend conversation history on each model call, so later turns cost more.",
        )
        apply_prompt_caching = st.toggle(
            "Apply prompt caching where available",
            value=False,
            help="Models with configured cache discounts reduce repeated input cost only.",
        )

    token_preview_rows = []
    for model_id in selected_labels:
        model = pricing_config.MODELS[model_id]
        token_counts = count_tokens_by_role(
            messages,
            model["tokenizer_provider"],
            model.get("tokenizer_model"),
        )
        token_preview_rows.append(
            {
                "Provider": model["provider"],
                "Model": model["model_name"],
                "System tokens": token_counts.get("system", 0),
                "User tokens": token_counts.get("user", 0),
                "Assistant tokens": token_counts.get("assistant", 0),
            }
        )
    if token_preview_rows:
        st.subheader("Parsed conversation token preview")
        st.dataframe(pd.DataFrame(token_preview_rows), use_container_width=True, hide_index=True)

    rows, skipped = cost_calculator.calculate_estimates(
        messages=messages,
        selected_model_ids=selected_labels,
        monthly_volume=int(monthly_volume),
        average_turns=int(average_turns),
        full_context_per_turn=full_context_per_turn,
        apply_prompt_caching=apply_prompt_caching,
    )

    for message in skipped:
        st.warning(message)

    if not rows:
        st.error("No selected models have configured pricing. Select at least one priced model.")
        return

    df = pd.DataFrame(rows)
    chart_df = df.copy()
    chart_df["Model label"] = chart_df["Provider"] + " - " + chart_df["Model"]
    chart_df["Monthly label"] = chart_df["Monthly cost"].map(lambda value: f"${value:,.0f}")

    st.subheader(f"Estimated monthly cost at {int(monthly_volume):,} conversations/month")
    bar = px.bar(
        chart_df,
        x="Monthly cost",
        y="Model label",
        color="Provider",
        color_discrete_map=PROVIDER_COLORS,
        orientation="h",
        text="Monthly label",
        title=f"Estimated monthly cost at {int(monthly_volume):,} conversations/month",
    )
    bar.update_layout(
        yaxis={"categoryorder": "total ascending", "title": ""},
        xaxis_title="Monthly cost (USD)",
        showlegend=True,
        plot_bgcolor="white",
        height=max(320, 80 + len(chart_df) * 54),
    )
    bar.update_xaxes(showgrid=False)
    bar.update_yaxes(showgrid=False)
    bar.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(bar, use_container_width=True)

    st.subheader("Detailed breakdown")
    display_df = df[
        [
            "Provider",
            "Model",
            "Input tokens/conv",
            "Output tokens/conv",
            "Input cost",
            "Output cost",
            "Monthly cost",
        ]
    ].copy()
    for column in ["Input cost", "Output cost", "Monthly cost"]:
        display_df[column] = display_df[column].map(lambda value: round(value, 2))
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.subheader("Volume sensitivity")
    volumes = [100, 300, 1_000, 3_000, 10_000, 30_000, 100_000]
    sensitivity_rows = []
    for row in rows:
        for volume in volumes:
            sensitivity_rows.append(
                {
                    "Conversations/month": volume,
                    "Monthly cost": row["Per conversation cost"] * volume,
                    "Model": f"{row['Provider']} - {row['Model']}",
                    "Provider": row["Provider"],
                }
            )
    sensitivity_df = pd.DataFrame(sensitivity_rows)
    line = px.line(
        sensitivity_df,
        x="Conversations/month",
        y="Monthly cost",
        color="Model",
        markers=True,
        log_x=True,
        title="Monthly cost sensitivity by volume",
    )
    line.update_layout(plot_bgcolor="white", xaxis_title="Conversations/month", yaxis_title="Monthly cost (USD)")
    line.update_xaxes(showgrid=False)
    line.update_yaxes(showgrid=False)
    st.plotly_chart(line, use_container_width=True)

    st.caption(
        "Token estimates for Anthropic and Gemini use provider token counters when API keys are configured; otherwise they use an approximate character heuristic."
    )


def run_pricing_updater() -> None:
    try:
        with st.spinner("Updating pricing from provider pages..."):
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("pricing_updater.py"))],
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
    except subprocess.TimeoutExpired:
        st.error("Pricing updater timed out after 90 seconds.")
        return

    if result.stdout:
        st.code(result.stdout, language="text")
    if result.stderr:
        st.code(result.stderr, language="text")

    if result.returncode == 0:
        refreshed = refresh_pricing_modules()
        if not refreshed:
            st.warning(
                "Pricing file was updated, but the app could not hot-reload it. "
                "Refresh the page or restart Streamlit to load the latest pricing."
            )
        st.success("Pricing updater finished. Review the output before pitching.")
    else:
        st.error(f"Pricing updater failed with exit code {result.returncode}.")


def refresh_pricing_modules() -> bool:
    global pricing_config
    global cost_calculator

    try:
        importlib.invalidate_caches()
        sys.modules["pricing"] = pricing_config
        sys.modules["cost"] = cost_calculator
        pricing_config = importlib.reload(pricing_config)
        cost_calculator = importlib.reload(cost_calculator)
    except Exception:
        return False
    return True


if __name__ == "__main__":
    main()
