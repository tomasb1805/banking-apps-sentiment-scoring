"""Release-level friction: which app version releases preceded the largest
post-release complaint spikes.

Reads a precomputed static snapshot (data/release_friction.csv) built from
SQL/04_spikes.sql, instead of querying BigQuery live. This page never holds
a cloud credential of any kind -- see utils/data.py's module docstring for
why the live-query mode this page used to have was removed rather than
hardened.
"""

import plotly.graph_objects as go
import streamlit as st

from utils.data import load_release_friction
from utils.state import keep
from utils.theme import current_palette, provider_colors, style

# Show at most this many releases per app in the ranked chart. Without a cap,
# the ranking is monopolised by whichever app ships most often (Tide releases
# roughly weekly and accounts for ~46% of all flagged days), which buries the
# cross-provider comparison this project is actually about.
TOP_N_PER_APP = 2
MAX_RELEASES = 15

palette = current_palette()
colors = provider_colors(palette)

st.title("Release-Level Friction")
st.caption("Largest post-release complaint spikes, 14-day window")
st.caption(
    "This page reads a precomputed snapshot (`data/release_friction.csv`) "
    "rather than querying BigQuery live -- this app doesn't ship a live-query "
    "mode anywhere, so it never needs a cloud credential to run."
)

spikes = load_release_friction()
if spikes.empty:
    st.info("No release-linked spikes found in the current snapshot.")
    st.stop()

# ------------------------------------------------------------- Page filter --

st.sidebar.subheader("Filters")
min_reviews = st.sidebar.slider(
    "Minimum reviews on the flagged day",
    min_value=1,
    max_value=10,
    key=keep("flt_min_reviews", 3),
    help=(
        "A day with a single review that happens to be negative scores a "
        "100% negative share, which isn't a spike -- it's noise. Raising "
        "this threshold keeps only flagged days with enough reviews to mean "
        "something. 87 of the 483 flagged days rest on a single review."
    ),
)

scoped = spikes[spikes["n"] >= min_reviews].copy()
if scoped.empty:
    st.warning(
        "No flagged days meet that minimum-reviews threshold. Lower it in the sidebar."
    )
    st.stop()

# How far above its own trailing baseline the day actually jumped. This, not
# the raw peak, is what the spike-detection query is measuring -- and ranking
# on it stops the chart filling up with low-volume 100% days.
scoped["lift"] = (scoped["neg_share"] - scoped["baseline"]) * 100

# --------------------------------------------------------- Ranked overview --

worst_idx = scoped.groupby(["app", "version", "release_date"])["lift"].idxmax()
summary = scoped.loc[
    worst_idx,
    ["app", "version", "release_date", "provider_group", "neg_share", "baseline", "n", "lift"],
].reset_index(drop=True)

flagged_days = (
    scoped.groupby(["app", "version", "release_date"])["date_review"]
    .nunique()
    .rename("n_flagged_days")
    .reset_index()
)
summary = summary.merge(flagged_days, on=["app", "version", "release_date"])
summary["peak_neg_share"] = summary["neg_share"] * 100
summary["baseline_pct"] = summary["baseline"] * 100

summary = summary.sort_values("lift", ascending=False)
summary = summary.groupby("app").head(TOP_N_PER_APP)
summary = summary.sort_values("lift", ascending=False).head(MAX_RELEASES).reset_index(drop=True)
summary["label"] = summary["app"] + " " + summary["version"]

st.subheader(f"Worst release-linked spikes — up to {TOP_N_PER_APP} per app")

fig = go.Figure()
for _, row in summary.iterrows():
    fig.add_trace(
        go.Scatter(
            x=[row["baseline_pct"], row["peak_neg_share"]],
            y=[row["label"], row["label"]],
            mode="lines",
            line=dict(color=palette["muted"], width=2),
            showlegend=False,
            hoverinfo="skip",
        )
    )
fig.add_trace(
    go.Scatter(
        x=summary["baseline_pct"],
        y=summary["label"],
        mode="markers",
        name="Rolling baseline",
        marker=dict(color=palette["muted"], size=9),
        hovertemplate="Baseline: %{x:.1f}%<extra></extra>",
    )
)
for group in ["TradBank", "NeoBank"]:
    subset = summary[summary["provider_group"] == group]
    if subset.empty:
        continue
    fig.add_trace(
        go.Scatter(
            x=subset["peak_neg_share"],
            y=subset["label"],
            mode="markers",
            name=f"{group} peak",
            marker=dict(color=colors[group], size=12, symbol="diamond"),
            customdata=subset[["lift", "n"]],
            hovertemplate=(
                "Peak: %{x:.1f}%<br>Jump above baseline: %{customdata[0]:.1f}pp"
                "<br>Reviews that day: %{customdata[1]}<extra></extra>"
            ),
        )
    )

fig.update_layout(
    height=560,
    xaxis_title="Negative-review share (%)",
    yaxis_title=None,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
)
fig = style(fig, palette)
fig.update_yaxes(autorange="reversed")
st.plotly_chart(fig, use_container_width=True)

st.caption(
    f"Ranked by the size of the jump above each release's own trailing "
    f"baseline, not by the raw peak — a release going from 5% to 20% is a "
    f"real signal, one already sitting at 18% going to 20% is not. Capped at "
    f"{TOP_N_PER_APP} releases per app so the ranking shows the fleet rather "
    f"than whichever app ships most often. "
    f"{summary['app'].nunique()} of {spikes['app'].nunique()} apps with "
    f"flagged releases appear at the current threshold."
)

# Rendered as an HTML table rather than st.dataframe on purpose: st.dataframe
# draws into a canvas grid that ignores page CSS, so it would stay light on a
# dark page and break the global theme.
table = summary[
    ["app", "version", "release_date", "provider_group",
     "n_flagged_days", "baseline_pct", "peak_neg_share", "lift", "n"]
].copy()
table["release_date"] = table["release_date"].dt.strftime("%Y-%m-%d")
for col in ("baseline_pct", "peak_neg_share", "lift"):
    table[col] = table[col].map("{:.1f}".format)
table.columns = [
    "App", "Version", "Released", "Group",
    "Flagged days", "Baseline %", "Peak %", "Jump pp", "Reviews",
]
st.markdown(
    table.to_html(index=False, classes="fl-table", border=0, escape=False),
    unsafe_allow_html=True,
)

# ---------------------------------------------------- Distribution by app --

st.divider()
st.subheader("How severe do flagged days get, by app?")

# Ordered TradBank first, then NeoBank, each by median severity, so the
# provider-group comparison reads left to right instead of being scattered.
medians = scoped.groupby("app")["neg_share"].median()
app_order = sorted(
    scoped["app"].unique(),
    key=lambda a: (0 if scoped.loc[scoped["app"] == a, "provider_group"].iloc[0] == "TradBank" else 1,
                   -medians[a]),
)

fig2 = go.Figure()
seen_groups = set()
for app in app_order:
    subset = scoped[scoped["app"] == app]
    group = subset["provider_group"].iloc[0]
    fig2.add_trace(
        go.Box(
            # x carries the app (so each box sits on its own category) while
            # name carries the provider group (so the legend reads TradBank /
            # NeoBank). Using name for the app is what previously put single
            # app names -- "Barclays", "Tide" -- in the legend.
            x=[app] * len(subset),
            y=subset["neg_share"] * 100,
            name=group,
            marker_color=colors[group],
            line=dict(color=colors[group]),
            fillcolor=palette["panel"],
            boxpoints="all",
            jitter=0.5,
            pointpos=0,
            marker=dict(size=5, opacity=0.55),
            legendgroup=group,
            showlegend=group not in seen_groups,
            hovertemplate=f"{app} ({group})<br>Negative share: %{{y:.1f}}%<extra></extra>",
        )
    )
    seen_groups.add(group)

fig2.update_layout(
    height=480,
    yaxis_title="Negative-review share on a flagged day (%)",
    xaxis_title=None,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    boxmode="overlay",
    boxgap=0.35,
)
fig2 = style(fig2, palette)
fig2.update_xaxes(categoryorder="array", categoryarray=app_order)
st.plotly_chart(fig2, use_container_width=True)

missing_apps = sorted(set(["Revolut", "Wise"]) - set(scoped["app"].unique()))
st.caption(
    "Each box covers all of an app's flagged days across every release, with "
    "the individual days plotted over it — a box plot fits this better than a "
    "per-release view, because most releases only trip the detector on a "
    "handful of days, too few to say anything about on their own. Navy is "
    "TradBank, teal is NeoBank."
    + (
        f" {' and '.join(missing_apps)} never appear: their review volume is "
        f"high enough that no single day moves the daily average far enough "
        f"above the trailing baseline to trip a threshold-based detector, "
        f"which is a limitation of this method rather than evidence of "
        f"friction-free releases."
        if missing_apps
        else ""
    )
)
st.caption(
    "Scope: releases from Aug 2025 - Aug 2026. Klarna is excluded from this "
    "analysis as a BNPL provider rather than a current-account app."
)
