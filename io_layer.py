"""
io_layer.py

This module handles all file ingestion, reading, and cleaning operations.
It abstracts the file system access (local or potentially cloud) and ensures
that only clean, valid DataFrames are passed to the application logic.
"""

import pandas as pd
import os
import glob

def get_available_files(folder_path):
    """
    Scans the given folder path for Excel files, excluding temporary or specific system files.

    Args:
        folder_path (str): The local directory path to scan.

    Returns:
        list: A list of valid file paths.
    """
    if not os.path.exists(folder_path):
        return []

    all_files = glob.glob(os.path.join(folder_path, "*.xls*"))
    valid_files = [
        f for f in all_files 
        if not os.path.basename(f).startswith('~')
        and "MASTER" not in f
        and "Matrix" not in f
        and "Combined" not in f
        and "Processed" not in f
        and "Graph" not in f
    ]
    return valid_files

def load_and_clean_data(file_path):
    """
    Reads an Excel file and standardizes column names.

    Args:
        file_path (str): The path to the Excel file.

    Returns:
        pd.DataFrame or None: A standardized DataFrame with columns 
        ['Date', 'Net P&L', 'Year', 'Month', 'Day', 'Drawdown %', 'Run-up'],
        or None if the file is invalid or cannot be read.
    """
    filename = os.path.basename(file_path)
    # Double check exclusion logic in case this is called directly
    if any(x in filename for x in ["MASTER", "Matrix", "Combined", "Heatmap", "Processed", "Graph"]):
        return None

    try:
        df = None
        try:
            # Try specific sheet name first
            df = pd.read_excel(file_path, sheet_name="List of trades")
        except ValueError:
            try:
                # Fallback to 4th sheet if exact name not found
                xls = pd.ExcelFile(file_path)
                if len(xls.sheet_names) >= 4:
                    sheet_name = xls.sheet_names[3]
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                else:
                    return None
            except:
                return None

        if df is None:
            return None

        df.columns = df.columns.str.strip()

        # Identify Key Columns
        date_col = next((c for c in df.columns if 'Date' in c or 'Time' in c), None)
        pnl_col = next((c for c in df.columns if 'Net P&L' in c or 'Profit' in c), None)
        drawdown_col = next((c for c in df.columns if 'Drawdown' in c and '%' in c), None)
        type_col = next((c for c in df.columns if 'Type' in c), None)

        # --- DETECT RUN-UP / MFE COLUMN ---
        runup_col = next((c for c in df.columns if any(
            k in c.lower() for k in ['run-up', 'run up', 'mfe', 'max profit', 'highest', 'max favorable'])), None)

        if not date_col or not pnl_col:
            return None

        # Filter by Type if exists
        if type_col:
            df = df[df[type_col].astype(str).str.contains('Exit', case=False, na=False)].copy()

        df[date_col] = pd.to_datetime(df[date_col])
        df['Year'] = df[date_col].dt.year
        df['Month'] = df[date_col].dt.month_name()
        df['Day'] = df[date_col].dt.day_name()

        # Rename logic
        rename_map = {date_col: 'Date', pnl_col: 'Net P&L'}
        if drawdown_col: 
            rename_map[drawdown_col] = 'Drawdown %'
        if runup_col: 
            rename_map[runup_col] = 'Run-up'

        df = df.rename(columns=rename_map)

        if 'Drawdown %' not in df.columns: 
            df['Drawdown %'] = 0
        if 'Run-up' not in df.columns: 
            df['Run-up'] = 0  # Default if missing

        return df[['Date', 'Net P&L', 'Year', 'Month', 'Day', 'Drawdown %', 'Run-up']]

    except Exception:
        return None
