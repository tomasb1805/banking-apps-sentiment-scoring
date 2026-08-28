CREATE OR REPLACE
  TABLE `fintech-reviews-analytics.fintech_app_reviews.transformed_review_metrics`
  AS
WITH unified_raw AS (
  SELECT
    app,
    app_version,
    reviewed_at,
    content
  FROM `fintech-reviews-analytics.fintech_app_reviews.raw_app_store_*`
  UNION ALL
  SELECT
    app,
    app_version,
    reviewed_at,
    content
  FROM `fintech-reviews-analytics.fintech_app_reviews.raw_google_play_*`
),
base_sentiment AS (
  SELECT
    app,
    app_version,
    DATE_TRUNC(DATE(TIMESTAMP(reviewed_at)), WEEK) AS review_week,
    CASE 
      WHEN LOWER(content) LIKE '%kyc%' OR LOWER(content) LIKE '%verification%' THEN 'KYC/Onboarding'
      WHEN LOWER(content) LIKE '%decline%' OR LOWER(content) LIKE '%card%' THEN 'Card Decline'
      WHEN LOWER(content) LIKE '%support%' OR LOWER(content) LIKE '%help%' THEN 'Customer Support'
      ELSE 'General UX'
    END AS friction_category
  FROM
    unified_raw
),
aggregated_metrics AS (
  SELECT
    app,
    app_version,
    review_week,
    friction_category,
    COUNT(*) AS total_reviews,
  FROM
    base_sentiment
  GROUP BY 1, 2, 3, 4
)
SELECT
  app,
  app_version,
  review_week,
  friction_category,
  total_reviews,
  /*
  avg_weekly_sentiment,
  LAG(avg_weekly_sentiment, 1) OVER (
    PARTITION BY app_name, app_version, friction_category 
    ORDER BY review_week
  ) AS prev_week_sentiment
  */
FROM
  aggregated_metrics;
