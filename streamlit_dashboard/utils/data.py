"""Data loading and feature engineering for the Friction Ledger dashboard.

This app reads exclusively from bundled, precomputed CSV snapshots in the
project's data/ folder -- there is no live-query mode and no cloud
credential of any kind involved anywhere in this app. That's a deliberate
choice, not a missing feature: a publicly deployed Streamlit app that holds
a durable BigQuery service-account key is a standing liability for very
little benefit on a portfolio piece, so the live-BigQuery mode this app
used to offer was removed entirely rather than hardened. See the README
for how to refresh these snapshots (an occasional, offline step you run
yourself -- never something the deployed app does).

Two scoping rules are applied at load time, so every page inherits them and
no chart can accidentally disagree with another:

- ANALYSIS WINDOW (Aug 2025 - Aug 2026). The scrape stopped each app on a
  review-count quota rather than a fixed start date, so per-app history
  depth varies wildly: ANNA Bank reaches back to 2020 and Tide to 2024,
  while most apps only start in Aug 2025 and NatWest not until Jan 2026.
  Those long tails are an artifact of how the scrape stopped, not a real
  difference in how long each bank has existed, and they make every
  cross-provider comparison misleading. The window is pinned to the twelve
  months where the fleet is genuinely comparable.
- EXCLUDED PROVIDERS. Klarna was dropped from this project's analysis
  earlier (it's a BNPL provider rather than a current-account app, so it
  doesn't belong in a NeoBank-vs-TradBank comparison) but its rows are
  still present in reviews_analyzed.csv. They're filtered out here, which
  is what removes the stray "Other" provider group from the filters.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Project root is two levels above this file (streamlit_dashboard/utils/data.py
# -> streamlit_dashboard/ -> project root, where the shared data/ folder lives).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "data" / "reviews_analyzed.csv"

# Precomputed export of SQL/04_spikes.sql's "negative_spikes" result -- the
# query that used to run live against BigQuery on the Release Friction page.
# Regenerate by re-running that query and re-exporting whenever the
# underlying review/release data is refreshed; see the README.
RELEASE_FRICTION_CSV_PATH = PROJECT_ROOT / "data" / "release_friction.csv"

# The analysis window. Reviews outside it are dropped at load time; the month
# sliders on every page are pinned to these bounds rather than to whatever
# the data happens to contain, so the window can't drift if the data is
# refreshed.
ANALYSIS_START = pd.Timestamp("2025-08-01", tz="UTC")
ANALYSIS_END = pd.Timestamp("2026-09-01", tz="UTC")  # exclusive upper bound
SLIDER_MIN = datetime(2025, 8, 1)
SLIDER_MAX = datetime(2026, 8, 1)

PROVIDER_MAP = {
    "Barclays": "TradBank",
    "HSBC": "TradBank",
    "Lloyds": "TradBank",
    "NatWest": "TradBank",
    "Monzo": "NeoBank",
    "Starling": "NeoBank",
    "Revolut": "NeoBank",
    "Wise": "NeoBank",
    "Tide": "NeoBank",
    "ANNA Bank": "NeoBank",
}

# Apps present in the source data but deliberately outside this analysis.
EXCLUDED_APPS = {"Klarna"}

REQUIRED_COLUMNS = {
    "app",
    "platform",
    "reviewed_at",
    "score",
    "primary_category",
    "vader_sentiment",
}

RELEASE_FRICTION_REQUIRED_COLUMNS = {
    "app",
    "version",
    "release_date",
    "date_review",
    "days_since",
    "n",
    "neg_share",
    "avg_vader",
    "baseline",
}


@st.cache_data(ttl=3600, show_spinner="Loading review data…")
def load_reviews() -> pd.DataFrame:
    """Load and enrich the bundled review-level dataset.

    Shows a friendly Streamlit error (rather than a raw stack trace) if the
    expected columns aren't present -- the most likely failure mode for
    anyone plugging in a different export of the underlying data.
    """
    if not CSV_PATH.exists():
        st.error(
            f"Couldn't find `{CSV_PATH.relative_to(PROJECT_ROOT)}`. "
            "Restore the bundled CSV at that path to run this app."
        )
        st.stop()
    df = pd.read_csv(CSV_PATH)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        st.error(
            "The loaded dataset is missing expected column(s): "
            f"{', '.join(sorted(missing))}. Check that data/reviews_analyzed.csv "
            "matches the schema this app expects."
        )
        st.stop()

    return _enrich(df)


@st.cache_data(ttl=3600, show_spinner="Loading release-friction snapshot…")
def load_release_friction() -> pd.DataFrame:
    """Load the precomputed release-vs-spike snapshot for the Release
    Friction page.

    This is a static export, not a live query -- see the module docstring.
    Only the flagged days that SQL/04_spikes.sql's QUALIFY clause selected
    are present (the days where a release's negative-review share jumped
    meaningfully above that release's own rolling baseline), so this data
    is sparse by design: it's a list of "this day was flagged," not a
    continuous daily series for every day since every release.
    """
    if not RELEASE_FRICTION_CSV_PATH.exists():
        st.error(
            f"Couldn't find `{RELEASE_FRICTION_CSV_PATH.relative_to(PROJECT_ROOT)}`. "
            "See the README for how to regenerate this snapshot from "
            "SQL/04_spikes.sql."
        )
        st.stop()
    df = pd.read_csv(RELEASE_FRICTION_CSV_PATH)

    missing = RELEASE_FRICTION_REQUIRED_COLUMNS - set(df.columns)
    if missing:
        st.error(
            "The release-friction snapshot is missing expected column(s): "
            f"{', '.join(sorted(missing))}. Check that data/release_friction.csv "
            "matches the output shape of SQL/04_spikes.sql."
        )
        st.stop()

    df = df.copy()
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df["date_review"] = pd.to_datetime(df["date_review"], errors="coerce")
    df = df.dropna(subset=["release_date", "date_review"])

    # Same scoping rules as the review data, so this page can't disagree
    # with the others about which providers and which months are in play.
    df = df[~df["app"].isin(EXCLUDED_APPS)]
    df = df[
        (df["release_date"] >= ANALYSIS_START.tz_localize(None))
        & (df["release_date"] < ANALYSIS_END.tz_localize(None))
    ]
    df["provider_group"] = df["app"].map(PROVIDER_MAP)
    return df.dropna(subset=["provider_group"])


def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["reviewed_at"] = pd.to_datetime(df["reviewed_at"], utc=True, errors="coerce")
    df = df.dropna(subset=["reviewed_at"])

    df = df[~df["app"].isin(EXCLUDED_APPS)]
    df = df[(df["reviewed_at"] >= ANALYSIS_START) & (df["reviewed_at"] < ANALYSIS_END)]

    # tz_convert(None) first: to_period() would drop the timezone anyway and
    # warn about it on every load. Month buckets are UTC-based by design.
    df["review_month"] = (
        df["reviewed_at"].dt.tz_convert(None).dt.to_period("M").dt.to_timestamp()
    )
    df["provider_group"] = df["app"].map(PROVIDER_MAP)
    # Anything still unmapped isn't part of this analysis; dropping it is
    # what keeps a stray "Other" group out of the provider filters.
    df = df.dropna(subset=["provider_group"])
    df["is_negative"] = (df["vader_sentiment"] == "negative").astype(int)

    df = _align_neobank_window(df)
    return df


def _align_neobank_window(df: pd.DataFrame) -> pd.DataFrame:
    """Trim NeoBank reviews to the date window where TradBank data also exists.

    The fixed analysis window above already does most of this work. This is
    the belt-and-braces guarantee: if the window or the underlying snapshot
    ever changes such that the TradBank apps still start later than the
    NeoBank ones, NeoBank rows are trimmed to the earliest TradBank review
    so the two lines always cover a comparable span. Without it, a
    NeoBank-vs-TradBank chart can show NeoBank history stretching back
    years with no TradBank line to compare it against -- an artifact of how
    the scrape stopped, not a real difference in how long each bank has had
    reviews. TradBank rows are never trimmed.
    """
    tradbank_start = df.loc[df["provider_group"] == "TradBank", "reviewed_at"].min()
    if pd.isna(tradbank_start):
        return df
    is_neobank = df["provider_group"] == "NeoBank"
    return df.loc[~is_neobank | (df["reviewed_at"] >= tradbank_start)]


def filter_reviews(
    df: pd.DataFrame,
    date_range: tuple,
    providers: list[str],
    platforms: list[str],
) -> pd.DataFrame:
    """Apply the shared sidebar filters.

    One filter row scopes every chart on a page -- deliberately not
    per-chart filters, so every chart on a page always reflects the same
    slice of data.

    The date filter compares whole months against `review_month`, matching
    what the slider actually offers. Comparing the slider's month-start
    values against raw timestamps would silently drop most of the final
    month (a slider set to Aug 2026 would cut everything after Aug 1st).
    """
    start, end = date_range
    start_month = pd.Timestamp(start).to_period("M").to_timestamp()
    end_month = pd.Timestamp(end).to_period("M").to_timestamp()
    mask = (
        df["review_month"].between(start_month, end_month)
        & df["provider_group"].isin(providers)
        & df["platform"].isin(platforms)
    )
    return df.loc[mask]
