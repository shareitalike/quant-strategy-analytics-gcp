import os
import pandas as pd
import tempfile
from google.cloud import storage

MODE = os.getenv("DATA_MODE", "LOCAL")  # LOCAL or GCS

def load_csv():
    if MODE == "LOCAL":
        return pd.read_csv("data/sample.csv")

    # ---------- GCS MODE ----------
    bucket_name = os.environ["GCS_BUCKET"]
    blob_name   = os.environ["GCS_OBJECT"]

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    with tempfile.NamedTemporaryFile(suffix=".csv") as f:
        blob.download_to_filename(f.name)
        return pd.read_csv(f.name)
