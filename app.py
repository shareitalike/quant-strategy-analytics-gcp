"""
app.py

Main entry point for the Quant Strategy Dashboard.
Cloud-native refactor:
- LOCAL mode → filesystem (dev)
- GCS mode   → Google Cloud Storage (Cloud Run safe)
"""
import os
import streamlit as st
import pandas as pd
import numpy as np

import io_layer
import metrics
import charts

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(page_title="Quant Strategy Dashboard", layout="wide", page_icon="🏛️")

# --- PROFESSIONAL CSS (unchanged) ---
st.markdown("""<style>/* CSS unchanged for brevity */</style>""", unsafe_allow_html=True)

# ==========================================
# 2. RUNTIME MODE
# ==========================================
DATA_MODE = os.getenv("DATA_MODE", "LOCAL")  # LOCAL | GCS

if DATA_MODE not in ("LOCAL", "GCS"):
    st.error("Invalid DATA_MODE. Use LOCAL or GCS.")
    st.stop()

# ==========================================
# 3. CACHED WRAPPERS
# ==========================================
@st.cache_data
def get_cached_leaderboard(all_dfs, file_names, start_date, end_date, investment, rf_rate, slippage):
    return metrics.get_optimized_leaderboard(
        all_dfs, file_names, start_date, end_date, investment, rf_rate, slippage
    )

@st.cache_data
def load_data_cached(source):
    """
    source:
      - LOCAL → file path
      - GCS   → blob name
    """
    return io_layer.load_and_clean_data(source)

# ==========================================
# 4. SIDEBAR CONTROLS
# ==========================================
st.sidebar.title("📊 Trading Dashboard")
st.sidebar.markdown("---")

st.sidebar.caption(f"📡 Data Mode: **{DATA_MODE}**")

# ---------- LOCAL MODE ----------
if DATA_MODE == "LOCAL":
    default_path = os.getenv("DATA_PATH", "./data")
    folder_path = st.sidebar.text_input("📂 Folder Path:", value=default_path)
    available_files = io_layer.get_available_files(folder_path)

# ---------- GCS MODE ----------
else:
    bucket = os.environ.get("GCS_BUCKET")
    prefix = os.environ.get("GCS_PREFIX", "")

    if not bucket:
        st.error("GCS_BUCKET environment variable not set")
        st.stop()

    st.sidebar.text_input("🪣 GCS Bucket", value=bucket, disabled=True)
    st.sidebar.text_input("📁 Prefix", value=prefix, disabled=True)

    available_files = io_layer.get_available_files_from_gcs(bucket, prefix)

# ---------- FILE SELECTION ----------
if not available_files:
    st.sidebar.error("No strategy files found")
    st.stop()

file_map = {os.path.basename(f): f for f in available_files}
file_names_only = list(file_map.keys())

all_selected = st.sidebar.checkbox("Select All Files", value=True)
selected_files_names = st.sidebar.multiselect(
    "Select Strategies:",
    options=file_names_only,
    default=file_names_only if all_selected else []
)
selected_files = [file_map[name] for name in selected_files_names]

# ---------- CAPITAL & PARAMETERS ----------
c_cap, c_rf = st.sidebar.columns(2)
investment = c_cap.number_input("💰 Initial Capital (₹):", value=125000, step=5000)
rf_rate = c_rf.number_input("🏦 Risk-Free Rate (%):", value=0.0, step=0.5)

with st.sidebar.expander("🛑 Reality Check (Costs & Taxes)", expanded=False):
    slippage = st.number_input("Cost per Trade (₹):", value=0.0, step=10.0)
    tax_rate = st.number_input("Tax / Fee Rate (%):", value=0.0, step=5.0)

use_compound = st.sidebar.checkbox("Enable Compounding (CAGR)", value=False)

# ==========================================
# 5. DATA LOAD
# ==========================================
if not selected_files:
    st.info("👈 Please select at least one file to begin.")
    st.stop()

st.title("📊 Quant Strategy Dashboard")

all_dfs = []
used_files = []

progress = st.sidebar.progress(0)

for i, source in enumerate(selected_files):
    df = load_data_cached(source)
    if df is not None:
        all_dfs.append(df)
        used_files.append(os.path.basename(source))
    progress.progress((i + 1) / len(selected_files))

progress.empty()

if not all_dfs:
    st.error("No valid data loaded.")
    st.stop()

# ==========================================
# 6. REMAINDER OF YOUR DASHBOARD
# ==========================================
# 🔒 EVERYTHING BELOW THIS LINE IS UNCHANGED
# Your metrics, tabs, charts, Monte Carlo, compounding,
# leaderboard, drawdowns, seasonality, etc. remain exactly as-is.
#
# (Use your existing logic verbatim from this point onward)
