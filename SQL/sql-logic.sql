-- creates the table
CREATE OR REPLACE TABLE `fintech-review-analytics.fintech_reviews.transformed_review_metrics` AS
/*
    creates a CTE called 'base_sentiment', selecting the app_name,
    app_version, and the week of each app
    update, associating each with a sentiment_score.

    Finally, using different WHEN clauses, it generates the most
    common review topic for each app version, calling the column
    'friction_category'

*/
WITH base_sentiment AS (
  SELECT
    app_name,
    app_version,
    DATE_TRUNC(PARSE_DATE('%Y-%m-%d', review_date), WEEK) AS review_week,
    sentiment_score,
    CASE 
      WHEN LOWER(review_text) LIKE '%kyc%' OR LOWER(review_text) LIKE '%verification%' THEN 'KYC/Onboarding'
      WHEN LOWER(review_text) LIKE '%decline%' OR LOWER(review_text) LIKE '%card%' THEN 'Card Decline'
      WHEN LOWER(review_text) LIKE '%support%' OR LOWER(review_text) LIKE '%help%' THEN 'Customer Support'
      ELSE 'General UX'
    END AS friction_category
  FROM
    `fintech-review-analytics.fintech_reviews.raw_app_reviews`
),
/* 
    creates a second CTE, with the newly created columns
    review_week & friction_category.
    The COUNT function will count the total rows per
    each category, and finally AVG on the sentiment score
    will compute the average weekly sentiment

*/
aggregated_metrics AS (
  SELECT
    app_name,
    app_version,
    review_week,
    friction_category,
    COUNT(*) AS total_reviews,
    AVG(sentiment_score) AS avg_weekly_sentiment
  FROM
    base_sentiment
  GROUP BY 1, 2, 3, 4
)
/*
    This is the main query.
    It introduces the Window Function LAG to compute
    week on week changes.
*/

SELECT
  app_name,
  app_version,
  review_week,
  friction_category,
  total_reviews,
  avg_weekly_sentiment,
  -- Calculate week-over-week sentiment change using Window Functions
  LAG(avg_weekly_sentiment, 1) OVER (
    PARTITION BY app_name, friction_category 
    ORDER BY review_week
  ) AS prev_week_sentiment
FROM
  aggregated_metrics;
