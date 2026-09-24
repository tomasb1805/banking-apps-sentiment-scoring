"""
Backfill scraper — closes the review-history coverage gap for Revolut, Wise, Barclays
and Lloyds so their monthly sentiment trend spans the same Aug 2025-Aug 2026 window as
Monzo and Starling (the two apps whose lines are already unbroken on the dashboard).

WHY THIS EXISTS
----------------
`scrape_app_reviews.ipynb` builds `data/raw/{platform}_{app}.csv` checkpoints by paging
backwards from the newest review until either (a) a per-app review quota is hit, or
(b) the page's dates fall before `CUTOFF`. Looking at `upload_data.py`'s FILES_TO_UPLOAD
comments ("original" vs. "newly added (fccc733)"), Revolut/Wise/Klarna were scraped in
one run and the other eight apps in a later one — each run's own quota governed how far
back that app's checkpoint reaches, not a shared, guaranteed start date. That is why some
apps' monthly lines start partway through the window: their checkpoint simply never paged
back far enough, not because reviews don't exist further back.

This script re-runs the SAME scraping logic already proven in scrape_app_reviews.ipynb
(same libraries, same RSS work-around for the App Store, same checkpoint/dedup logic) but:
  1. Scoped to only Revolut, Wise, Barclays, Lloyds (ANNA Bank and Tide are intentionally
     excluded — see note below and the dashboard notice this pairs with).
  2. Uses a Google Play quota high enough (BACKFILL_TARGET_PER_APP) that CUTOFF, not the
     quota, is what actually stops the walk-back — so it pages as far into the past as the
     store will allow, up to the shared window start.
  3. Reuses the existing checkpoint files at `data/raw/`, so it EXTENDS them (dedup by
     review_id) rather than re-collecting or duplicating anything already saved.
  4. Rebuilds `data/reviews_all.csv` afterwards from ALL 11 apps' checkpoints (not just the
     4 backfilled ones), so nothing else in the pipeline is disturbed.

WHY ANNA BANK AND TIDE ARE EXCLUDED
------------------------------------
Their gap is a different problem: they are simply small apps with few real-world reviews
(113 and 176 total, vs. thousands for the others). Re-running this same backfill against
them would not manufacture history that doesn't exist — it would just re-confirm the low
volume. The dashboard's Module 2 panel now carries a plain-language notice about this so
it isn't confused with a scraping/coverage bug.

WHAT THIS SCRIPT DOES NOT DO
------------------------------
It only backfills the raw scrape. After it finishes, re-run (in this order):
  1. analyze_app_reviews.ipynb  — regenerates data/reviews_analyzed.csv (VADER + category
     tagging) from the refreshed data/reviews_all.csv.
  2. upload_data.py             — re-uploads the changed raw CSVs (and reviews_analyzed.csv,
     however that table is refreshed) to BigQuery.
  3. Re-run the SQL/*.sql exports the dashboard's CSVs are drawn from.

ENVIRONMENT
------------
Run inside the project's existing `fintech-app-reviews` conda environment (see
environment.yml) — same one the scraper and analysis notebooks already use:
    conda activate fintech-app-reviews
    python scrape_backfill_coverage_gap.py

This script was written and reviewed in a sandboxed session with no network access to
Apple/Google, so it has NOT been run end-to-end. Start with SMOKE_TEST=True below to
confirm both scrapers still work against the live endpoints before doing the full run —
the same "smoke test first" step the original notebook recommends.
"""

from datetime import datetime
import os
import time

import pandas as pd
from google_play_scraper import reviews as gp_reviews, Sort as GPSort
from app_store_scraper import AppStore as _BaseAppStore

# ============================================================
# CONFIG
# ============================================================
SMOKE_TEST = False          # True = ~10 reviews/app first, to confirm the scrapers still work.
                            # Flip to False for the real backfill run.

COUNTRY = "gb"              # Apple storefront code for the UK is "gb", NOT "uk".
LANG = "en"
DATA_DIR = "data"
RAW_DIR = os.path.join(DATA_DIR, "raw")
SLEEP_GPLAY = 0.5
SLEEP_RSS = 0.5

APP_STORE_CAP_PER_APP = 500        # Hard limit of Apple's public RSS feed (10 pages x 50).
BACKFILL_TARGET_PER_APP = 100_000  # Deliberately far above any real review count, so the
                                    # CUTOFF date below — not this number — is what stops
                                    # the Google Play walk-back.

# Same window start already used elsewhere in this project's scraper notebook, and the
# start of the "Aug 2025-Aug 2026" window the dashboard reports.
CUTOFF = datetime(2025, 8, 9)

# Only the four apps with a real backfill opportunity (ANNA Bank / Tide are volume-limited,
# not coverage-limited — see module docstring).
APPS = {
    "Revolut":  {"gplay": "com.revolut.revolut",              "ios_id": 932493382,  "ios_name": "revolut"},
    "Wise":     {"gplay": "com.transferwise.android",         "ios_id": 612261027,  "ios_name": "wise"},
    "Barclays": {"gplay": "com.barclays.android.barclaysmobilebanking", "ios_id": 536248734, "ios_name": "barclays"},
    "Lloyds":   {"gplay": "com.grppl.android.shell.CMBlloydsTSB73",     "ios_id": 469964520, "ios_name": "lloyds-mobile-banking"},
}

# Full 11-app roster (matches scrape_app_reviews.ipynb) — needed only for the final
# "rebuild reviews_all.csv" step, so apps outside this backfill aren't dropped from the
# combined file.
ALL_APPS = list(APPS.keys()) + ["Klarna", "Starling", "Tide", "Monzo", "ANNA Bank", "NatWest", "HSBC"]

os.makedirs(RAW_DIR, exist_ok=True)
print("Backfilling:", ", ".join(APPS.keys()))
print("Reviews older than", CUTOFF.date(), "are excluded")
print("SMOKE_TEST =", SMOKE_TEST)


# ============================================================
# App Store adapter (RSS work-around) — identical to scrape_app_reviews.ipynb.
# app-store-scraper 0.3.5 calls Apple's authenticated amp-api and gets 401; this
# subclass reads the public RSS customer-reviews feed instead.
# ============================================================
class RSSAppStore(_BaseAppStore):
    _request_host = "itunes.apple.com"

    def build_url(self, page):
        return (f"https://itunes.apple.com/{self.country}/rss/customerreviews/"
                f"page={page}/id={self.app_id}/sortBy=mostRecent/json")

    def _parse_data(self, after):
        feed = self._response.json().get("feed", {})
        entries = feed.get("entry", [])
        if isinstance(entries, dict):
            entries = [entries]
        for e in entries:
            review = {
                "id":        e.get("id", {}).get("label", ""),
                "userName":  e.get("author", {}).get("name", {}).get("label", ""),
                "rating":    int(e.get("im:rating", {}).get("label", 0)),
                "title":     e.get("title", {}).get("label", ""),
                "review":    e.get("content", {}).get("label", ""),
                "appVersion": e.get("im:version", {}).get("label", ""),
                "date":      datetime.strptime(e["updated"]["label"], "%Y-%m-%dT%H:%M:%S%z"),
            }
            if after and review["date"].replace(tzinfo=None) < after:
                continue
            self.reviews.append(review)
            self.reviews_count += 1
            self._fetched_count += 1


# ============================================================
# Normalisation + checkpoint helpers — identical to scrape_app_reviews.ipynb, so the
# output schema matches data/raw/*.csv exactly and merges cleanly.
# ============================================================
COLS = ["platform", "app", "review_id", "user_name", "content", "score",
        "thumbs_up", "app_version", "reviewed_at", "reply", "replied_at"]


def norm_gplay(app, r):
    return {
        "platform": "google_play", "app": app,
        "review_id": r.get("reviewId"), "user_name": r.get("userName"),
        "content": r.get("content"), "score": r.get("score"),
        "thumbs_up": r.get("thumbsUpCount"),
        "app_version": r.get("reviewCreatedVersion") or r.get("appVersion"),
        "reviewed_at": pd.to_datetime(r.get("at"), utc=True, errors="coerce"),
        "reply": r.get("replyContent"), "replied_at": r.get("repliedAt"),
    }


def norm_ios(app, r):
    return {
        "platform": "app_store", "app": app,
        "review_id": r.get("id"), "user_name": r.get("userName"),
        "content": " | ".join(x for x in [r.get("title"), r.get("review")] if x),
        "score": r.get("rating"), "thumbs_up": None,
        "app_version": r.get("appVersion"),
        "reviewed_at": pd.to_datetime(r.get("date"), utc=True, errors="coerce"),
        "reply": None, "replied_at": None,
    }


def load_existing(path):
    """Return (rows, seen_ids) loaded from a previously saved checkpoint CSV — this is
    what lets a backfill EXTEND an existing file rather than re-collecting duplicates."""
    if os.path.exists(path) and os.path.getsize(path) > 0:
        df = pd.read_csv(path)
        if len(df):
            return df.to_dict("records"), set(df["review_id"].dropna().astype(str))
    return [], set()


def save_progress(path, rows):
    pd.DataFrame(rows, columns=COLS).to_csv(path, index=False)


# ============================================================
# Scrapers — identical logic to scrape_app_reviews.ipynb.
# ============================================================
def scrape_google_play(app, target, cutoff):
    package = APPS[app]["gplay"]
    path = os.path.join(RAW_DIR, f"google_play_{app}.csv")
    rows, seen = load_existing(path)
    start_n = len(rows)
    print(f"[google_play/{app}] starting (have {start_n} rows, extending backward)")
    token = None
    while len(rows) < target:
        try:
            page, token = gp_reviews(package, lang=LANG, country=COUNTRY,
                                      sort=GPSort.NEWEST, count=199,
                                      continuation_token=token)
        except Exception as e:
            print("  ! page error, retrying in 5s:", e)
            time.sleep(5)
            continue
        if not page:
            print("  empty page — no more reviews available from the store")
            break
        new = []
        for r in page:
            rid = r.get("reviewId")
            if rid in seen:
                continue
            seen.add(rid)
            date = pd.to_datetime(r.get("at"), utc=True, errors="coerce")
            if cutoff is not None and date is not None and date.tz_localize(None) < cutoff:
                continue
            new.append(norm_gplay(app, r))
        rows.extend(new)
        save_progress(path, rows)
        print(f"  page: {len(page)} fetched, +{len(new)} kept, total {len(rows)}")
        if token is None:
            print("  no more pages available")
            break
        if cutoff is not None and page[-1]["at"].date() < cutoff.date():
            print(f"  reached {cutoff.date()} cutoff — backfill target met for this app")
            break
        time.sleep(SLEEP_GPLAY)
    print(f"[google_play/{app}] done: {start_n} -> {len(rows)} rows (+{len(rows)-start_n})")
    return rows


def scrape_app_store(app, target, cutoff):
    cfg = APPS[app]
    path = os.path.join(RAW_DIR, f"app_store_{app}.csv")
    rows, seen = load_existing(path)
    start_n = len(rows)
    print(f"[app_store/{app}] starting (have {start_n} rows) — RSS feed caps at "
          f"{APP_STORE_CAP_PER_APP}, so a high-volume app may already be at the ceiling")
    store = RSSAppStore(country=COUNTRY, app_name=cfg["ios_name"], app_id=cfg["ios_id"])
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", "Accept": "application/json"}
    for page in range(1, 11):
        if len(rows) >= target:
            break
        try:
            store.reviews = []
            store._get(store.build_url(page), headers=headers)
            store._parse_data(cutoff)
        except Exception as e:
            print(f"  ! page {page} error, retrying in 5s:", e)
            time.sleep(5)
            continue
        new = []
        for r in store.reviews:
            rid = r.get("id")
            if rid in seen:
                continue
            seen.add(rid)
            new.append(norm_ios(app, r))
        if new:
            rows.extend(new)
            save_progress(path, rows)
        print(f"  page {page}: +{len(new)} kept, total {len(rows)}")
        time.sleep(SLEEP_RSS)
    print(f"[app_store/{app}] done: {start_n} -> {len(rows)} rows (+{len(rows)-start_n})")
    return rows


# ============================================================
# Run
# ============================================================
def main():
    all_new_rows = []
    for app in APPS:
        gp_target = 10 if SMOKE_TEST else BACKFILL_TARGET_PER_APP
        as_target = 10 if SMOKE_TEST else APP_STORE_CAP_PER_APP
        all_new_rows.extend(scrape_google_play(app, gp_target, CUTOFF))
        all_new_rows.extend(scrape_app_store(app, as_target, CUTOFF))
        print()

    if SMOKE_TEST:
        print("Smoke test complete — inspect the printed page-by-page output above, then "
              "set SMOKE_TEST = False and re-run for the full backfill.")
        return

    # ---- Rebuild data/reviews_all.csv from every app's checkpoint, not just the 4
    #      that were backfilled, so nothing else in the pipeline is disturbed. ----
    frames = []
    for app in ALL_APPS:
        for platform in ("google_play", "app_store"):
            path = os.path.join(RAW_DIR, f"{platform}_{app}.csv")
            if os.path.exists(path) and os.path.getsize(path) > 0:
                frames.append(pd.read_csv(path))

    if not frames:
        print("No checkpoint files found — nothing to combine.")
        return

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["reviewed_at"])
    df["reviewed_at"] = pd.to_datetime(df["reviewed_at"], utc=True, errors="coerce")
    df = df.drop_duplicates(subset=["platform", "review_id"]).reset_index(drop=True)

    out_path = os.path.join(DATA_DIR, "reviews_all.csv")
    df.to_csv(out_path, index=False)
    print(f"Saved {out_path} — {len(df)} rows total across all {len(ALL_APPS)} apps")
    print()
    print("Backfilled apps' new date range:")
    for app in APPS:
        sub = df[df["app"] == app]
        if len(sub):
            print(f"  {app}: {sub['reviewed_at'].min().date()} -> {sub['reviewed_at'].max().date()} "
                  f"({len(sub)} rows)")
    print()
    print("Next steps: re-run analyze_app_reviews.ipynb, then upload_data.py, then the "
          "SQL/*.sql exports the dashboard reads from.")


if __name__ == "__main__":
    main()
