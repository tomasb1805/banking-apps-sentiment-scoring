"""Home: fleet-wide KPIs and the headline friction trend.

This page used to show two stacked panels -- average star rating and
negative-review share. They were near-perfect mirrors of each other (a month
with more negative reviews is a month with a lower average), so the second
panel carried no information the first didn't, and the "opposite direction"
shape read as a finding when it was really an identity.

It now shows one metric, split by provider group: the share of reviews that
land as negative, TradBank vs NeoBank, on one shared axis. That's the
project's actual subject -- friction -- and the comparison between the two
kinds of provider is the question the whole dashboard exists to answer.
Average rating still appears as a KPI above, and gets its own trend on the
Sentiment by Provider page, so nothing was lost by dropping the second panel.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from utils.data import SLIDER_MAX, SLIDER_MIN, filter_reviews, load_reviews
from utils.state import keep
from utils.theme import current_palette, provider_colors, style

palette = current_palette()
reviews = load_reviews()

st.sidebar.subheader("Filters")
date_range = st.sidebar.slider(
    "Review month",
    min_value=SLIDER_MIN,
    max_value=SLIDER_MAX,
    format="MMM YYYY",
    key=keep("flt_month", (SLIDER_MIN, SLIDER_MAX)),
    help=(
        "The analysis is pinned to Aug 2025 - Aug 2026, the twelve months "
        "where every app in the fleet has comparable review coverage."
    ),
)
provider_options = sorted(reviews["provider_group"].dropna().unique())
providers = st.sidebar.multiselect(
    "Provider group", provider_options, key=keep("flt_providers", provider_options)
)
platform_options = sorted(reviews["platform"].dropna().unique())
platforms = st.sidebar.multiselect(
    "Platform", platform_options, key=keep("flt_platforms", platform_options)
)

filtered = filter_reviews(reviews, date_range, providers, platforms)

if filtered.empty:
    st.warning("No reviews match the current filters. Widen the date range or selection.")
    st.stop()

# ------------------------------------------------------------------- KPIs --

st.title("The Friction Ledger")
st.caption("Sentiment and complaint-driver analysis across 10 UK banking apps")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Reviews analyzed", f"{len(filtered):,}")
k2.metric("Average score", f"{filtered['score'].mean():.2f} / 5")
k3.metric("Negative-review share", f"{filtered['is_negative'].mean() * 100:.1f}%")
k4.metric("Apps in view", filtered["app"].nunique())

st.divider()

# ------------------------------------------------- Friction by provider --

st.subheader("Negative-review share by month")

monthly = (
    filtered.groupby(["review_month", "provider_group"])["is_negative"]
    .mean()
    .mul(100)
    .reset_index()
)

colors = provider_colors(palette)

fig = go.Figure()
for group in ["TradBank", "NeoBank"]:
    subset = monthly[monthly["provider_group"] == group].sort_values("review_month")
    if subset.empty:
        continue
    fig.add_trace(
        go.Scatter(
            x=subset["review_month"],
            y=subset["is_negative"],
            mode="lines+markers",
            name=group,
            line=dict(color=colors[group], width=2.4),
            marker=dict(size=8),
            hovertemplate=f"{group}<br>%{{x|%b %Y}}<br>%{{y:.1f}}% negative<extra></extra>",
        )
    )

fig.update_layout(
    height=520,
    yaxis_title="Share of reviews that are negative (%)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    hovermode="x unified",
)
fig = style(fig, palette)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "One metric, one axis, two comparable series -- both lines are the same "
    "unit, so the gap between them is real rather than an artifact of two "
    "scales. Average star rating isn't shown alongside it because the two "
    "move as near-mirrors of each other; it has its own trend on **Sentiment "
    "by Provider**."
)
st.caption(
    "The sidebar filters carry over between this page, **Sentiment by "
    "Provider** and **Complaint Drivers**. **Release Friction** works from "
    "release-level data and has its own filter."
)
st.caption(
    "Scope: Aug 2025 - Aug 2026, the window where all ten apps have "
    "comparable review coverage. Klarna is excluded from this analysis as a "
    "BNPL provider rather than a current-account app."
)
