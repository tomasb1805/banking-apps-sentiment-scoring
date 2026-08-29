-- =====================================================================
-- Q2 — VADER Evolution (Line Chart, Monthly, App + Superset)
-- Source: app_reviews_sentiment_analysis, Klarna excluded
-- Output: one row per (app|provider_group) x review_month, for a 12-line
-- chart (10 apps + TradBank/NeoBank supersets).
-- =====================================================================

WITH provider_map AS (
  SELECT * FROM UNNEST([
    STRUCT('Barclays' AS app, 'TradBank' AS provider_group),
    ('HSBC','TradBank'), ('Lloyds','TradBank'), ('NatWest','TradBank'),
    ('Monzo','NeoBank'), ('Starling','NeoBank'), ('Revolut','NeoBank'),
    ('Wise','NeoBank'), ('Tide','NeoBank'), ('ANNA Bank','NeoBank')
  ])
),
base AS (
  SELECT
    r.app,
    m.provider_group,
    DATE_TRUNC(DATE(r.reviewed_at), MONTH) AS review_month,
    r.vader_compound,
    r.vader_sentiment
  FROM `fintech-reviews-analytics.fintech_app_reviews.app_reviews_sentiment_analysis` r
  JOIN provider_map m USING (app)
  WHERE r.app != 'Klarna'
),
monthly_app AS (
  SELECT
    app,
    review_month,
    AVG(vader_compound) AS avg_vader,
    COUNT(*) AS n,
    AVG(IF(vader_sentiment = 'negative', 1, 0)) AS neg_share
  FROM base
  GROUP BY 1, 2
),
monthly_group AS (
  SELECT
    provider_group AS app,
    review_month,
    AVG(vader_compound) AS avg_vader,
    COUNT(*) AS n,
    AVG(IF(vader_sentiment = 'negative', 1, 0)) AS neg_share
  FROM base
  GROUP BY 1, 2
)
SELECT
  *,
  LAG(avg_vader) OVER (PARTITION BY app ORDER BY review_month) AS prev_month,
  avg_vader - LAG(avg_vader) OVER (PARTITION BY app ORDER BY review_month) AS delta
FROM (
  SELECT * FROM monthly_app
  UNION ALL
  SELECT * FROM monthly_group
)
ORDER BY app, review_month;
