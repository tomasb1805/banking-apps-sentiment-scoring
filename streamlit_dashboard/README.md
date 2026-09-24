# The Friction Ledger — Streamlit Dashboard

A Streamlit companion to the Tableau workbook in this repo, built from the
same sentiment analysis of UK banking app reviews. Where the Tableau
workbook demonstrates BI-tool fluency, this app expresses the same analysis
in the project's native stack -- Python, pandas, and Plotly -- deployed as a
shareable, interactive web app.

This app reads exclusively from bundled CSV snapshots in the project's
`data/` folder. There is no live-query mode and no cloud credential of any
kind anywhere in this app -- see "Why no live BigQuery mode" below.

## Structure

```
streamlit_dashboard/
├── dashboard.py                  # Entry point: navigation + global theme
├── views/
│   ├── home.py                     # Fleet-wide KPIs + friction trend
│   ├── sentiment_by_provider.py    # NeoBank vs. TradBank score trend
│   ├── complaint_drivers.py        # Category share-of-negative gap
│   └── release_friction.py         # Post-release complaint spikes
├── utils/
│   ├── data.py                   # Loading, caching, scoping, feature engineering
│   ├── state.py                  # Filter persistence across sections
│   └── theme.py                  # Light/dark palettes, global CSS, Plotly styling
├── .streamlit/
│   └── config.toml               # Browser-theme passthrough
├── requirements.txt
└── .gitignore
```

Sections are wired up explicitly with `st.navigation` in `dashboard.py`
rather than through Streamlit's automatic `pages/` folder. With `pages/`,
each section is its own top-level script, so anything drawn in the sidebar
belongs to whichever section is showing -- which is why the appearance
control used to reset itself every time you changed section. `dashboard.py`
runs on every interaction regardless of section, so global controls stay
put, and section titles are set explicitly instead of being derived from
filenames.

## Quick start

No cloud setup required, ever -- the app runs entirely from two bundled
files in the project's `data/` folder: `reviews_analyzed.csv` (used by every
page) and `release_friction.csv` (used only by *Release Friction*).

```bash
cd streamlit_dashboard
pip install -r requirements.txt
streamlit run dashboard.py
```

If you already work in the project's conda environment, it carries these same
pins, so there's nothing extra to install:

```bash
conda env create -f ../environment.yml   # or `conda env update` if it exists
conda activate fintech-app-reviews
streamlit run dashboard.py
```

The two dependency files are deliberate, not duplication. `environment.yml` is
the local development environment for the whole project -- scraping, analysis,
the BigQuery upload and this dashboard. `requirements.txt` is the manifest
Streamlit Community Cloud installs from, and it stays minimal on purpose:
Community Cloud uses the first dependency file it finds, checking the app
entrypoint's directory before the repo root, so deleting this file would make
the deployed app install the entire analysis pipeline -- including the Google
Cloud SDKs that this app was deliberately stripped of. Keep the three pins in
sync across both files.

Open the URL Streamlit prints (usually `http://localhost:8501`).

## Scope of the analysis

Two scoping rules are applied once, in `utils/data.py`, so every page
inherits them and no two charts can disagree about what's in view:

- **Aug 2025 – Aug 2026.** The scrape behind this data stopped each app on a
  review-count quota rather than a fixed start date, so per-app history
  depth varies wildly — ANNA Bank reaches back to 2020 and Tide to 2024,
  while most apps start in Aug 2025 and NatWest not until Jan 2026. Those
  long tails are an artifact of how the scrape stopped, not a real
  difference in how long each bank has existed, and they make every
  cross-provider comparison misleading. The month sliders are pinned to
  these bounds rather than derived from the data, so the window can't drift
  if the snapshots are refreshed.
- **Klarna excluded.** It's a BNPL provider rather than a current-account
  app, so it doesn't belong in a NeoBank-vs-TradBank comparison. It was
  dropped from this project's SQL earlier but its rows are still present in
  `reviews_analyzed.csv`; filtering it at load time is what removes the
  stray "Other" provider group from the filters.

## Light and dark themes

The **Appearance** control (Auto / Light / Dark) in the sidebar themes the
whole page, not just the charts, and holds its setting as you move between
sections. Auto follows the viewer's browser/OS dark-mode preference, read via
`st.context.theme`.

Streamlit has no runtime theme API, so `apply_theme()` in `utils/theme.py`
injects CSS that repaints the app background, sidebar, headings, captions and
metrics alongside handing the matching palette to every figure. It runs once
in `dashboard.py`, before any section renders. The Release Friction table is
rendered as HTML for the same reason: `st.dataframe` draws into a canvas grid
that ignores page CSS and would stay light on a dark page.

The dark palette is a separately chosen set, not an automatic flip of the
light one. It uses a dark slate surface rather than near-black and text below
pure white, so the page reads calm rather than glaring. The two series
colours were picked by running a categorical-palette validator against that
surface rather than by eye, because the obvious approach of just lightening
the brand colours failed: a pale navy and a bright teal sit too close
together in colour space (normal-vision ΔE 12.5, under the 15 floor) and are
genuinely hard to tell apart. The pair now in use passes every check --
lightness band, chroma floor, colour-blind separation, normal-vision
separation and contrast against the surface -- while staying recognisably
navy-for-TradBank and teal-for-NeoBank.

## Deploying to Streamlit Community Cloud

1. Push this repo (or just this `streamlit_dashboard/` subfolder) to GitHub.
2. At [share.streamlit.io](https://share.streamlit.io), create a new app
   pointing at `streamlit_dashboard/dashboard.py`.

That's it -- no secrets to configure. The deployed app is exactly as safe
to expose publicly as the CSVs it's built from, because that's all it reads.

## Why no live BigQuery mode

An earlier version of this app could optionally query the live BigQuery
warehouse this project publishes to, using a service-account key stored in
Streamlit's secrets manager. That was removed. A downloadable
service-account key is a long-lived bearer credential: anyone who obtained
it could use it from anywhere until it was manually revoked, and scoping
its IAM role narrowly (read-only, single dataset) limits the blast radius
but doesn't remove the exposure of holding a durable secret inside a
publicly deployed app at all. For a portfolio piece, that's a real, standing
liability for very little payoff -- "the chart also works with a live
query" isn't worth a credential sitting in a third-party secrets manager.

Instead, every page -- including *Release Friction*, which previously only
worked in BigQuery mode -- now reads a precomputed snapshot. To refresh a
snapshot after the underlying data changes, re-run the relevant query in
BigQuery yourself (an occasional, manual, offline step) and overwrite the
CSV:

- `data/reviews_analyzed.csv` is produced by `analyze_app_reviews.ipynb`.
- `data/release_friction.csv` is the `negative_spikes` result of
  `SQL/04_spikes.sql`, exported to CSV with these columns: `app`, `version`,
  `release_date`, `date_review`, `days_since`, `n`, `neg_share`,
  `avg_vader`, `baseline`.

If you want a "look, it queries live data" flourish for a demo, the safer
way to do it is a small serverless proxy (e.g. Cloud Run using its own
attached service identity, which needs no downloadable key at all) that the
app calls over HTTPS -- keeping the durable BigQuery credential inside GCP
rather than inside Streamlit's secrets manager. That's a meaningfully
different security posture than embedding the BigQuery client directly in a
publicly deployed Streamlit app, and it's out of scope for this project.

## A design note: what the Home chart shows

The Home page originally plotted average star rating and negative-review
share as two stacked panels. Two different units on two different scales
were deliberately never combined into one dual-axis chart -- that was
flagged during this project's Tableau work as the most common charting
anti-pattern, because aligning two arbitrary scales invents a correlation
that isn't in the data.

The two panels had a subtler problem: they were near-mirrors of each other.
A month with more negative reviews is a month with a lower average, so the
second panel carried no information the first didn't, and its
opposite-direction shape read as a finding when it was really an identity.

Home now shows one metric split by provider group -- negative-review share
for TradBank vs NeoBank, two series of the same unit on one shared axis.
That is the project's actual subject, and the comparison between the two
kinds of provider is the question the dashboard exists to answer. Average
rating remains as a KPI above the chart and gets its own trend, in the same
two-series form, on the Sentiment by Provider page.

## A design note: the Release Friction charts

**The ranked chart** shows each flagged release as two dots — its own
rolling baseline negative-review share and the peak it hit within 14 days of
release — connected by a line, rather than a single bar of the peak value
alone. A bar showing only the peak would make a release that jumped from 5%
to 20% look identical to one that jumped from 18% to 20%; the dumbbell shape
keeps the "how far from that release's own normal" comparison visible, which
is what the underlying spike-detection query is actually measuring. Releases
are therefore ranked by that jump, not by the raw peak.

Two further choices keep the ranking readable and honest:

- **A minimum-reviews threshold** (sidebar, default 3). A day with one
  review that happens to be negative scores a 100% negative share — 87 of
  the 483 flagged days rest on a single review. Ranking on raw peak without
  this threshold produces a chart that is entirely 100% ties, ordered
  arbitrarily.
- **A cap of two releases per app.** Tide ships roughly weekly and accounts
  for ~46% of all flagged days, so an uncapped ranking is almost entirely
  Tide regardless of how it's sorted. The cap surfaces the fleet instead;
  the table below the chart carries the underlying numbers.

**The distribution chart** is a box plot per app of how severe its flagged
days get, with individual days plotted over each box. A box plot suits this
better than a per-release view because most releases only trip the detector
on a handful of days — too few to say anything about individually, but
enough to describe a distribution once pooled across an app's releases.

Note that Revolut and Wise never appear on this page. Their review volume is
high enough that no single day moves the daily average far enough above the
trailing baseline to trip a threshold-based detector — a limitation of the
detection method, not evidence that their releases are friction-free.
