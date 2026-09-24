-- =====================================================================
-- Q4 — Version Rollout vs Negative Spikes (14-Day Window)
-- Source: app_reviews_sentiment_analysis (reviews) + app_updates_release
-- (releases). Klarna removed from source; no filter needed.
-- NOTE: baseline is a 14-row trailing average computed AFTER restricting
-- to the post-release window, so it is most meaningful when an app's
-- releases are more than ~14 days apart (no overlapping rollout windows).
-- =====================================================================

WITH rel AS (
  SELECT app, version, DATE(release_date) AS release_date
  FROM `fintech-reviews-analytics.fintech_app_reviews.app_updates_release`
),
daily AS (
  SELECT
    app,
    DATE(reviewed_at) AS d,
    AVG(vader_compound) AS avg_vader,
    COUNT(*) AS n,
    AVG(IF(vader_sentiment = 'negative', 1, 0)) AS neg_share
  FROM `fintech-reviews-analytics.fintech_app_reviews.app_reviews_sentiment_analysis`
  GROUP BY 1, 2
)
SELECT
  r.app,
  r.version,
  r.release_date,
  d.d,
  DATE_DIFF(d.d, r.release_date, DAY) AS days_since,
  d.n,
  d.neg_share,
  d.avg_vader,
  AVG(d.neg_share) OVER (
    PARTITION BY r.app ORDER BY d.d ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING
  ) AS baseline
FROM rel r
JOIN daily d
  ON d.app = r.app
  AND d.d BETWEEN r.release_date AND DATE_ADD(r.release_date, INTERVAL 14 DAY)
QUALIFY d.neg_share > baseline + 0.15 OR d.avg_vader < baseline - 0.2;

-- Monthly rollout summary: release cadence per app
SELECT
  app,
  DATE_TRUNC(DATE(release_date), MONTH) AS release_month,
  COUNT(*) AS n_releases
FROM `fintech-reviews-analytics.fintech_app_reviews.app_updates_release`
GROUP BY 1, 2
ORDER BY app, release_month;
