-- =====================================================================
-- Q3 — Complaint Volume Bar Chart (Competitor Analysis)
-- Source: app_reviews_sentiment_analysis, Klarna excluded
-- General Praise / Uncategorized excluded — this is a complaint-only view.
-- =====================================================================

WITH provider_map AS (
  SELECT * FROM UNNEST([
    STRUCT('Barclays' AS app, 'TradBank' AS provider_group),
    ('HSBC','TradBank'), ('Lloyds','TradBank'), ('NatWest','TradBank'),
    ('Monzo','NeoBank'), ('Starling','NeoBank'), ('Revolut','NeoBank'),
    ('Wise','NeoBank'), ('Tide','NeoBank'), ('ANNA Bank','NeoBank')
  ])
)
SELECT
  m.provider_group,
  r.app,
  r.platform,
  r.primary_category,
  COUNT(*) AS n_reviews,
  AVG(r.vader_compound) AS mean_compound,
  AVG(IF(r.vader_sentiment = 'negative', 1, 0)) AS negative_share
FROM `fintech-reviews-analytics.fintech_app_reviews.app_reviews_sentiment_analysis` r
JOIN provider_map m USING (app)
WHERE r.app != 'Klarna'
  AND r.primary_category NOT IN ('General Praise', 'Uncategorized')
GROUP BY 1, 2, 3, 4
ORDER BY m.provider_group, n_reviews DESC;

-- Secondary: TradBank vs NeoBank "biggest complaint category" comparison
WITH provider_map AS (
  SELECT * FROM UNNEST([
    STRUCT('Barclays' AS app, 'TradBank' AS provider_group),
    ('HSBC','TradBank'), ('Lloyds','TradBank'), ('NatWest','TradBank'),
    ('Monzo','NeoBank'), ('Starling','NeoBank'), ('Revolut','NeoBank'),
    ('Wise','NeoBank'), ('Tide','NeoBank'), ('ANNA Bank','NeoBank')
  ])
)
SELECT
  m.provider_group,
  r.primary_category,
  COUNT(*) AS n_reviews
FROM `fintech-reviews-analytics.fintech_app_reviews.app_reviews_sentiment_analysis` r
JOIN provider_map m USING (app)
WHERE r.app != 'Klarna'
  AND r.primary_category NOT IN ('General Praise', 'Uncategorized')
GROUP BY 1, 2
ORDER BY m.provider_group, n_reviews DESC;

-- Audit variant: multi-label reviews attribute to every category they carry,
-- not just primary_category — use to sanity-check the primary_category tie-break
-- (analyze_app_reviews.ipynb:577) isn't hiding a bigger complaint elsewhere.
WITH provider_map AS (
  SELECT * FROM UNNEST([
    STRUCT('Barclays' AS app, 'TradBank' AS provider_group),
    ('HSBC','TradBank'), ('Lloyds','TradBank'), ('NatWest','TradBank'),
    ('Monzo','NeoBank'), ('Starling','NeoBank'), ('Revolut','NeoBank'),
    ('Wise','NeoBank'), ('Tide','NeoBank'), ('ANNA Bank','NeoBank')
  ])
),
exploded AS (
  SELECT
    r.app,
    m.provider_group,
    r.review_id,
    cat AS category
  FROM `fintech-reviews-analytics.fintech_app_reviews.app_reviews_sentiment_analysis` r
  JOIN provider_map m USING (app),
    UNNEST(SPLIT(NULLIF(r.categories, ''), ';')) AS cat
  WHERE r.app != 'Klarna'
)
SELECT
  provider_group,
  app,
  category,
  COUNT(DISTINCT review_id) AS n_reviews
FROM exploded
GROUP BY 1, 2, 3
ORDER BY provider_group, n_reviews DESC;
