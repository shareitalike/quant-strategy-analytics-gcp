"""
io_layer.py

Handles all file ingestion, reading, and cleaning operations.
Supports:
- LOCAL filesystem (development)
- GCS (Cloud Run / production, no FUSE)
"""

import pandas as pd
import os
import glob
import tempfile

from google.cloud import storage


# =====================================================
# 1. FILE DISCOVERY
# =====================================================
def get_available_files(folder_path):
    """
    LOCAL MODE:
    Scans a local folder path for Excel files.
    """
    if not os.path.exists(folder_path):
        return []

    all_files = glob.glob(os.path.join(folder_path, "*.xls*"))
    return _filter_valid_files(all_files)


def get_available_files_from_gcs(bucket_name, prefix=""):
    """
    GCS MODE:
    Lists Excel files from a GCS bucket + prefix.
    """
    client = storage.Client()
    blobs = client.list_blobs(bucket_name, prefix=prefix)

    files = [blob.name for blob in blobs if blob.name.lower().endswith((".xls", ".xlsx"))]
    return _filter_valid_files(files)


def _filter_valid_files(file_list):
    """
    Applies exclusion rules consistently for LOCAL and GCS.
    """
    return [
        f for f in file_list
        if not os.path.basename(f).startswith("~")
        and all(x not in f for x in [
            "MASTER", "Matrix", "Combined", "Processed", "Graph", "Heatmap"
        ])
    ]


# =====================================================
# 2. LOAD + CLEAN DATA
# =====================================================
def load_and_clean_data(source):
    """
    Loads and cleans an Excel file.

    source:
      - LOCAL → filesystem path
      - GCS   → blob name (bucket resolved via env var)

    Returns:
        pd.DataFrame or None
    """
    # ---------- LOCAL ----------
    if os.path.exists(source):
        return _load_excel(source)

    # ---------- GCS ----------
    return _load_excel_from_gcs(source)


def _load_excel_from_gcs(blob_name):
    """
    Downloads a GCS object to a temp file and processes it.
    """
    bucket_name = os.environ.get("GCS_BUCKET")
    if not bucket_name:
        return None

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
            blob.download_to_filename(tmp.name)
            return _load_excel(tmp.name)

    except Exception:
        return None


# =====================================================
# 3. CORE CLEANING LOGIC (UNCHANGED)
# =====================================================
def _load_excel(file_path):
    """
    Core Excel reading + normalization logic.
    """
    filename = os.path.basename(file_path)

    if any(x in filename for x in [
        "MASTER", "Matrix", "Combined", "Heatmap", "Processed", "Graph"
    ]):
        return None

    try:
        df = None

        # Try known sheet first
        try:
            df = pd.read_excel(file_path, sheet_name="List of trades")
        except ValueError:
            xls = pd.ExcelFile(file_path)
            if len(xls.sheet_names) >= 4:
                df = pd.read_excel(file_path, sheet_name=xls.sheet_names[3])
            else:
                return None

        if df is None:
            return None

        df.columns = df.columns.str.strip()

        # Identify columns dynamically
        date_col = next((c for c in df.columns if 'Date' in c or 'Time' in c), None)
        pnl_col = next((c for c in df.columns if 'Net P&L' in c or 'Profit' in c), None)
        drawdown_col = next((c for c in df.columns if 'Drawdown' in c and '%' in c), None)
        type_col = next((c for c in df.columns if 'Type' in c), None)

        runup_col = next(
            (c for c in df.columns if any(k in c.lower() for k in [
                'run-up', 'run up', 'mfe', 'max profit', 'highest', 'max favorable'
            ])),
            None
        )

        if not date_col or not pnl_col:
            return None

        # Filter exits only
        if type_col:
            df = df[df[type_col].astype(str).str.contains('Exit', case=False, na=False)].copy()

        df[date_col] = pd.to_datetime(df[date_col])

        df['Year'] = df[date_col].dt.year
        df['Month'] = df[date_col].dt.month_name()
        df['Day'] = df[date_col].dt.day_name()

        rename_map = {date_col: 'Date', pnl_col: 'Net P&L'}
        if drawdown_col:
            rename_map[drawdown_col] = 'Drawdown %'
        if runup_col:
            rename_map[runup_col] = 'Run-up'

        df = df.rename(columns=rename_map)

        if 'Drawdown %' not in df.columns:
            df['Drawdown %'] = 0.0
        if 'Run-up' not in df.columns:
            df['Run-up'] = 0.0

        return df[['Date', 'Net P&L', 'Year', 'Month', 'Day', 'Drawdown %', 'Run-up']]

    except Exception:
        return None
