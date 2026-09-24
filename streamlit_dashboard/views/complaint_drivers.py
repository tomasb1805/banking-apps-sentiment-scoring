"""Where complaints differ: category share of negative reviews,
NeoBank vs. TradBank.
"""

import plotly.graph_objects as go
import streamlit as st

from utils.data import SLIDER_MAX, SLIDER_MIN, filter_reviews, load_reviews
from utils.state import keep
from utils.theme import current_palette, style

palette = current_palette()

st.title("Where Complaints Differ")
st.caption(
    "Percentage-point gap in each category's share of negative reviews "
    "(NeoBank minus TradBank)"
)

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

negative = filtered[filtered["is_negative"] == 1]
if negative.empty:
    st.info("No negative reviews in the current filter selection.")
    st.stop()

# This chart is a difference between two groups, so it only means what the
# title says when both are in view. With one group filtered out the "gap"
# is measured against nothing -- say so rather than drawing bars that look
# like a comparison.
groups_in_view = set(negative["provider_group"].unique())
if len(groups_in_view) < 2:
    only = next(iter(groups_in_view))
    st.info(
        f"Only **{only}** is selected, so there's nothing to compare against: "
        f"the bars below show {only}'s own share of negative reviews per "
        f"category, not a gap. Select both provider groups in the sidebar for "
        f"the comparison this page is built for."
    )

share = negative.groupby(["provider_group", "primary_category"]).size().rename("n").reset_index()
totals = negative.groupby("provider_group").size().rename("total")
share = share.merge(totals, on="provider_group")
share["pct_of_negative"] = share["n"] / share["total"] * 100

pivot = share.pivot(index="primary_category", columns="provider_group", values="pct_of_negative").fillna(0.0)
for col in ("NeoBank", "TradBank"):
    if col not in pivot.columns:
        pivot[col] = 0.0
pivot["gap"] = pivot["NeoBank"] - pivot["TradBank"]
pivot = pivot[pivot.index != "Uncategorized"].sort_values("gap")

if pivot.empty:
    st.info("No named categories to compare for the current filters.")
    st.stop()

colors = [palette["teal"] if g > 0 else palette["navy"] for g in pivot["gap"]]

fig = go.Figure(
    go.Bar(
        x=pivot["gap"],
        y=pivot.index,
        orientation="h",
        marker_color=colors,
        text=[f"{g:+.1f}pp" for g in pivot["gap"]],
        textposition="outside",
        textfont=dict(color=palette["ink"]),
        hovertemplate="%{y}<br>Gap: %{x:+.1f}pp<extra></extra>",
    )
)
fig.add_vline(x=0, line_color=palette["muted"], line_width=1)
fig.update_layout(
    height=480,
    xaxis_title="Percentage-point gap in share of negative reviews (NeoBank − TradBank)",
    yaxis_title=None,
)
fig = style(fig, palette)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Teal bars: categories NeoBanks are hit by more. Navy bars: categories "
    "TradBanks are hit by more -- the same two colours that identify the "
    "groups everywhere else in this dashboard. 'Uncategorized' is excluded to "
    "keep focus on named complaint categories."
)
st.caption(
    "Scope: Aug 2025 - Aug 2026, the window where all ten apps have "
    "comparable review coverage. Klarna is excluded from this analysis as a "
    "BNPL provider rather than a current-account app."
)
