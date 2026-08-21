import os
import pandas as pd
from google.cloud import bigquery
# from google.cloud import secretmanager_v1



# Set GCP Credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp-key.json"

# Initialize Client
client = bigquery.Client()
table_id = "fintech-review-analytics.fintech_reviews.raw_app_reviews"

# Sample DataFrame (Replace with your scraped data)
df = pd.read_csv("scraped_reviews.csv")

# Define Ingestion Job Config
job_config = bigquery.LoadJobConfig(
    write_disposition="WRITE_TRUNCATE", # Replaces table if exists
    autodetect=True,
)

# Load to BigQuery
job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
job.result()  # Wait for completion

print(f"Loaded {job.output_rows} rows into {table_id}.")
