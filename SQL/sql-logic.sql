-- =====================================================================
-- transformed_review_metrics
-- Fintech App Reviews — monthly sentiment/category rollup for Looker Studio
-- Source of truth: app_reviews_sentiment_analysis (VADER-enriched).
-- Do NOT derive sentiment/category from raw_app_store_*/raw_google_play_*
-- — those hold only the pre-enrichment fields.
-- Scope: 10 UK banking apps (provider_map below). Klarna (BNPL, non-comparable)
-- was removed from the source dataset upstream -- no filter needed here.
-- Grain: app x review_month x primary_category
-- Regenerated: 2026-08-28
-- =====================================================================

CREATE OR REPLACE TABLE `fintech-reviews-analytics.fintech_app_reviews.transformed_review_metrics` AS

WITH provider_map AS (
  SELECT * FROM UNNEST([
    STRUCT('Barclays' AS app, 'TradBank' AS provider_group),
    ('HSBC','TradBank'), ('Lloyds','TradBank'), ('NatWest','TradBank'),
    ('Monzo','NeoBank'), ('Starling','NeoBank'), ('Revolut','NeoBank'),
    ('Wise','NeoBank'), ('Tide','NeoBank'), ('ANNA Bank','NeoBank')
  ])
),

monthly_metrics AS (
  SELECT
    r.app,
    m.provider_group,
    DATE_TRUNC(DATE(r.reviewed_at), MONTH) AS review_month,
    r.primary_category,
    COUNT(*) AS n_reviews,
    COUNTIF(r.platform = 'app_store')   AS n_ios,
    COUNTIF(r.platform = 'google_play') AS n_android,
    AVG(r.score)            AS avg_score,
    AVG(r.vader_compound)   AS avg_vader_compound,
    AVG(r.vader_neg)        AS avg_vader_neg,
    AVG(r.vader_neu)        AS avg_vader_neu,
    AVG(r.vader_pos)        AS avg_vader_pos,
    AVG(IF(r.vader_sentiment = 'negative', 1, 0)) AS negative_share,
    AVG(IF(r.vader_sentiment = 'positive', 1, 0)) AS positive_share,
    AVG(IF(r.vader_sentiment = 'neutral',  1, 0)) AS neutral_share
  FROM `fintech-reviews-analytics.fintech_app_reviews.app_reviews_sentiment_analysis` r
  JOIN provider_map m USING (app)
  GROUP BY 1, 2, 3, 4
  -- Risk mitigation: ANNA Bank / Tide have low monthly review volume.
  -- Drop app/month/category cells too thin (<=20 reviews) to be a reliable
  -- signal, rather than surfacing noisy averages on the dashboard.
  HAVING COUNT(*) > 20
)

SELECT
  app,
  provider_group,
  review_month,
  primary_category,
  n_reviews,
  n_ios,
  n_android,
  avg_score,
  avg_vader_compound,
  avg_vader_neg,
  avg_vader_neu,
  avg_vader_pos,
  negative_share,
  positive_share,
  neutral_share,
  -- NOTE: because the HAVING clause above already dropped thin months,
  -- LAG here compares each month to the previous *surviving* month for
  -- that app+category, not strictly the prior calendar month.
  LAG(avg_vader_compound) OVER (
    PARTITION BY app, primary_category ORDER BY review_month
  ) AS prev_month_avg_vader_compound,
  avg_vader_compound - LAG(avg_vader_compound) OVER (
    PARTITION BY app, primary_category ORDER BY review_month
  ) AS vader_compound_delta
FROM monthly_metrics
ORDER BY app, primary_category, review_month;
