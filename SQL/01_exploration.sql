-- =====================================================================
-- Q1 — Initial Data Exploration 
-- Source: app_reviews_sentiment_analysis, Klarna excluded
-- Run each SELECT independently in the BigQuery console.
-- =====================================================================

-- 1a. Overall shape: counts, date range, distinct apps/platforms
-- NOTE: app_version is NOT a column on app_reviews_sentiment_analysis
-- (it exists only on the raw_app_store_*/raw_google_play_* tables), so the
-- "% NULL app_version" check from the original plan is omitted here.
SELECT
  COUNT(*) AS total_reviews,
  MIN(DATE(reviewed_at)) AS min_review_date,
  MAX(DATE(reviewed_at)) AS max_review_date,
  COUNT(DISTINCT app) AS n_apps,
  COUNT(DISTINCT platform) AS n_platforms
FROM `fintech-reviews-analytics.fintech_app_reviews.app_reviews_sentiment_analysis`
WHERE app != 'Klarna';

-- 1b. Score histogram (1-5 stars)
SELECT
  score,
  COUNT(*) AS n_reviews
FROM `fintech-reviews-analytics.fintech_app_reviews.app_reviews_sentiment_analysis`
WHERE app != 'Klarna'
GROUP BY score
ORDER BY score;

-- 2. Platform x App matrix, avg review length
SELECT
  app,
  platform,
  COUNT(*) AS n_reviews,
  AVG(LENGTH(content)) AS avg_content_length
FROM `fintech-reviews-analytics.fintech_app_reviews.app_reviews_sentiment_analysis`
WHERE app != 'Klarna'
GROUP BY app, platform
ORDER BY app, platform;

-- 3. provider_group counts (TradBank vs NeoBank)
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
  COUNT(*) AS n_reviews
FROM `fintech-reviews-analytics.fintech_app_reviews.app_reviews_sentiment_analysis` r
JOIN provider_map m USING (app)
WHERE r.app != 'Klarna'
GROUP BY m.provider_group
ORDER BY m.provider_group;

-- 4. primary_category distribution
-- (validates against notebook: General Praise ~22k, Uncategorized ~10.6k
-- — analyze_app_reviews.ipynb:460)
SELECT
  primary_category,
  COUNT(*) AS n_reviews
FROM `fintech-reviews-analytics.fintech_app_reviews.app_reviews_sentiment_analysis`
WHERE app != 'Klarna'
GROUP BY primary_category
ORDER BY n_reviews DESC;

-- 5. Multi-label audit: explode ';'-joined categories, count multi-label reviews
-- (validates against notebook: n_categories > 1 => 197 rows — analyze_app_reviews.ipynb)
WITH exploded AS (
  SELECT
    review_id,
    n_categories,
    cat AS category
  FROM `fintech-reviews-analytics.fintech_app_reviews.app_reviews_sentiment_analysis`,
    UNNEST(SPLIT(NULLIF(categories, ''), ';')) AS cat
  WHERE app != 'Klarna'
)
SELECT
  category,
  COUNT(DISTINCT review_id) AS n_reviews,
  COUNTIF(n_categories > 1) AS n_reviews_multi_label
FROM exploded
GROUP BY category
ORDER BY n_reviews DESC;

-- 6. VADER compound score vs star rating correlation
-- (validates against notebook: broadly positive/negative split — analyze_app_reviews.ipynb:360)
SELECT
  score,
  COUNT(*) AS n_reviews,
  AVG(vader_compound) AS avg_vader_compound
FROM `fintech-reviews-analytics.fintech_app_reviews.app_reviews_sentiment_analysis`
WHERE app != 'Klarna'
GROUP BY score
ORDER BY score;
