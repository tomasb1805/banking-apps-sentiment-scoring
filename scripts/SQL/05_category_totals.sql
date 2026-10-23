-- 05_category_totals.sql: complete counts per app and category, no group-size filter
WITH provider_map AS (
  SELECT * FROM UNNEST([
    STRUCT('Barclays' AS app, 'TradBank' AS provider_group),
    ('HSBC','TradBank'), ('Lloyds','TradBank'), ('NatWest','TradBank'),
    ('Monzo','NeoBank'), ('Starling','NeoBank'), ('Revolut','NeoBank'),
    ('Wise','NeoBank'), ('Tide','NeoBank'), ('ANNA Bank','NeoBank')
  ])
)
SELECT
  r.app,
  m.provider_group,
  r.primary_category,
  COUNT(*) AS n_reviews,
  COUNTIF(r.vader_sentiment = 'negative') AS n_negative,
  SUM(r.score) AS sum_score,            -- for the Avg Rating tile
  SUM(r.vader_compound) AS sum_vader    -- for the Avg VADER Sentiment tile
FROM `fintech-reviews-analytics.fintech_app_reviews.app_reviews_sentiment_analysis` r
JOIN provider_map m USING (app)
WHERE DATE(r.reviewed_at) BETWEEN '2025-08-01' AND '2026-08-31'
GROUP BY 1, 2, 3;