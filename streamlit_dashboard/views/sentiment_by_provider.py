"""Sentiment trend split by provider group (NeoBank vs. TradBank).

Both lines share one continuous axis because both series are the same unit
(average star rating), so a single shared axis is the honest,
information-preserving choice: no arbitrary second scale is needed.
"""

import plotly.graph_objects as go
import streamlit as st

from utils.data import SLIDER_MAX, SLIDER_MIN, filter_reviews, load_reviews
from utils.state import keep
from utils.theme import current_palette, provider_colors, style

palette = current_palette()

st.title("Sentiment Trend: NeoBank vs. TradBank")

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
    st.warning("No reviews match the current filters.")
    st.stop()

monthly = (
    filtered.groupby(["review_month", "provider_group"])["score"]
    .mean()
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
            y=subset["score"],
            mode="lines+markers",
            name=group,
            line=dict(color=colors.get(group, palette["navy"]), width=2.4),
            marker=dict(size=8),
            hovertemplate=f"{group}<br>%{{x|%b %Y}}<br>%{{y:.2f}} / 5<extra></extra>",
        )
    )

fig.update_layout(
    height=520,
    yaxis_title="Average score",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    hovermode="x unified",
)
fig = style(fig, palette)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Average star rating, the satisfaction side of the same story the Home "
    "page tells with negative-review share. Both series are the same unit, so "
    "they share one axis."
)
st.caption(
    "Scope: Aug 2025 - Aug 2026. The scrape behind this data stopped each "
    "app on a review-count quota rather than a fixed start date, so "
    "low-volume apps (ANNA Bank, Tide) reached years further back than "
    "high-volume ones -- a scraping artifact, not a real difference in how "
    "long each bank has existed. Pinning the window to these twelve months "
    "keeps the two lines comparable."
)
