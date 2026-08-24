import json
import os
import pandas as pd
from google.cloud import bigquery
from google.cloud import secretmanager
from google.oauth2 import service_account

# Configuration
SECRET_ID = "gcp-key"
VERSION_ID = "latest"

PROJECT_ID = "fintech-reviews-analytics"
DATASET_ID = "fintech_app_reviews"
LOCATION = "europe-west2"

# Path to your raw data directory relative to project root
DATA_DIR = "./data"
# "./data/raw"

# Explicit list of your CSV files and their target BigQuery table
# names

FILES_TO_UPLOAD = {
    # App Store reviews - original

    # "app_store_Klarna.csv": "raw_app_store_klarna",
    # "app_store_Revolut.csv": "raw_app_store_revolut",
    # "app_store_Wise.csv": "raw_app_store_wise",

    # App Store reviews - newly added (fccc733)

    # "app_store_ANNA Bank.csv": "raw_app_store_anna_bank",
    # "app_store_Barclays.csv": "raw_app_store_barclays",
    # "app_store_HSBC.csv": "raw_app_store_hsbc",
    # "app_store_Lloyds.csv": "raw_app_store_lloyds",
    # "app_store_Monzo.csv": "raw_app_store_monzo",
    # "app_store_NatWest.csv": "raw_app_store_natwest",
    # "app_store_Starling.csv": "raw_app_store_starling",
    # "app_store_Tide.csv": "raw_app_store_tide",

    # Google Play reviews - original

    # "google_play_Klarna.csv": "raw_google_play_klarna",
    # "google_play_Revolut.csv": "raw_google_play_revolut",
    # "google_play_Wise.csv": "raw_google_play_wise",

    # Google Play reviews - newly added (fccc733)

    # "google_play_ANNA Bank.csv": "raw_google_play_anna_bank",
    # "google_play_Barclays.csv": "raw_google_play_barclays",
    # "google_play_HSBC.csv": "raw_google_play_hsbc",
    # "google_play_Lloyds.csv": "raw_google_play_lloyds",
    # "google_play_Monzo.csv": "raw_google_play_monzo",
    # "google_play_NatWest.csv": "raw_google_play_natwest",
    # "google_play_Starling.csv": "raw_google_play_starling",
    
    # iOS changelogs

    # "ios_Klarna.csv": "raw_ios_klarna",
    # "ios_Revolut.csv": "raw_ios_revolut",
    # "ios_Wise.csv": "raw_ios_wise",

    # iOS changelogs - newly added (c250046)
    # "ios_ANNA Bank.csv": "raw_ios_anna_bank",
    # "ios_Barclays.csv": "raw_ios_barclays",
    # "ios_HSBC.csv": "raw_ios_hsbc",
    # "ios_Lloyds.csv": "raw_ios_lloyds",
    # "ios_Monzo.csv": "raw_ios_monzo",
    # "ios_NatWest.csv": "raw_ios_natwest",
    # "ios_Starling.csv": "raw_ios_starling",
    # "ios_Tide.csv": "raw_ios_tide",
    
    "ios_changelogs.csv": "app_updates_release",
    "reviews_analyzed.csv": "app_reviews_sentiment_analysis"
}


def fetch_credentials_from_secret_manager(project_id: str, secret_id: str, version_id: str = "latest"):
    """
    Retrieves service account JSON credentials from Secret Manager and
    returns a google.oauth2.service_account.Credentials object.
    """
    # 1. Initialize Secret Manager Client
    secret_client = secretmanager.SecretManagerServiceClient()
    
    # 2. Construct the secret resource path
    secret_detail_path = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    
    # 3. Access the secret payload
    response = secret_client.access_secret_version(request={"name": secret_detail_path})
    
    # 4. Decode the payload bytes into a dictionary
    secret_payload = response.payload.data.decode("UTF-8")
    service_account_info = json.loads(secret_payload)
    
    # 5. Build Google Service Account Credentials from dictionary
    credentials = service_account.Credentials.from_service_account_info(service_account_info)
    
    return credentials

def upload_fintech_raw_tables():
    # Initialize BigQuery Client using local gcloud authentication or ADC
    client = bigquery.Client(project=PROJECT_ID)
    
    print(f"Starting batch upload for dataset: {PROJECT_ID}.{DATASET_ID}\n" + "="*60)

    for csv_file, table_name in FILES_TO_UPLOAD.items():
        file_path = os.path.join(DATA_DIR, csv_file)
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"

        # Verify file exists locally before uploading
        if not os.path.exists(file_path):
            print(f"Warning: File not found at {file_path}. Skipping...")
            continue

        print(f"Processing file: {csv_file}")
        print(f"Target Table : {table_id}")

        try:
            # Read CSV using Pandas (automatically handles multiline review text & quotes)
            df = pd.read_csv(file_path, dtype={"review_id": str})

            # Define BigQuery Load Configuration
            job_config = bigquery.LoadJobConfig(
                write_disposition="WRITE_TRUNCATE",  # Overwrites existing table on re-run
                autodetect=True,                     # Automatically detects schema types
            )

            # Execute load job
            job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
            job.result()  # Block and wait for execution to complete

            print(f"Success: Loaded {job.output_rows:,} rows into {table_name}.\n")

        except Exception as e:
            print(f"Error uploading {csv_file}: {e}\n")

    print("="*60 + "\nBatch upload complete!")

if __name__ == "__main__":
    upload_fintech_raw_tables()
