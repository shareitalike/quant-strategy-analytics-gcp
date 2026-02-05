"""
app.py

Main entry point for the Quant Strategy Dashboard.
Orchestrates the UI, handles user interaction, and delegates logic to
io_layer, metrics, and charts modules.
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

# --- PROFESSIONAL CSS ---
st.markdown("""
<style>
    /* 1. App Background */
    .stApp { background-color: #f8fafc; }

    /* 2. Metrics Styling */
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important; 
        font-weight: 700 !important;
        color: #0f172a;
        font-family: 'Segoe UI', sans-serif;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        color: #64748b;
        font-weight: 500;
    }

    /* 3. Cards/Containers */
    .css-1r6slb0 {
        background-color: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* 4. Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px; background-color: transparent; padding: 10px 0px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px; white-space: pre-wrap; background-color: #ffffff; border-radius: 6px;
        color: #64748b; font-weight: 600; border: 1px solid #e2e8f0;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563EB !important; color: #ffffff !important; border-color: #2563EB !important;
    }

    /* 5. Sidebar Polish */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)


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
    """Wrapper to cache the leaderboard calculation."""
    return metrics.get_optimized_leaderboard(all_dfs, file_names, start_date, end_date, investment, rf_rate, slippage)

@st.cache_data
def load_data_cached(file_path):
    """Wrapper to cache file loading."""
    return io_layer.load_and_clean_data(file_path)


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

if not available_files:
    if folder_path: # Only show error if user tried to input something
        st.sidebar.error("Invalid Folder Path or No Files Found")
else:
    # Process file list
    import os # Needed primarily for basename here in UI logic
    file_map = {os.path.basename(f): f for f in available_files}
    file_names_only = list(file_map.keys())

    container = st.sidebar.container()
    all_selected = st.sidebar.checkbox("Select All Files", value=True)

    if all_selected:
        selected_files_names = st.sidebar.multiselect("Select Strategies:", options=file_names_only,
                                                      default=file_names_only)
    else:
        selected_files_names = st.sidebar.multiselect("Select Strategies:", options=file_names_only, default=[])

    selected_files = [file_map[name] for name in selected_files_names]


# ==========================================
# 4. MAIN DASHBOARD RENDER
# ==========================================
if 'selected_files' in locals() and selected_files:
    if len(selected_files) == 1:
        st.title(f"{os.path.basename(selected_files[0]).replace('.xlsx', '')}")
    else:
        st.title(f"📊 Combined Strategy Analysis ({len(selected_files)} Files)")

    all_dfs = []
    used_files = []
    load_bar = st.sidebar.progress(0)
    
    for i, f in enumerate(selected_files):
        d = load_data_cached(f)
        if d is not None:
            all_dfs.append(d)
            used_files.append(os.path.basename(f))
        load_bar.progress((i + 1) / len(selected_files))
    load_bar.empty()

    if all_dfs:
        # CONSOLIDATE DATA
        master_df = pd.concat(all_dfs).sort_values('Date').reset_index(drop=True)

        if not master_df.empty:
            st.sidebar.markdown("---")
            st.sidebar.subheader("📅 Time Filter")

            min_date = master_df['Date'].min().to_pydatetime()
            max_date = master_df['Date'].max().to_pydatetime()

            start_date, end_date = st.sidebar.slider(
                "Select Date Range:", min_value=min_date, max_value=max_date, value=(min_date, max_date),
                format="MMM YYYY"
            )

            mask = (master_df['Date'] >= pd.to_datetime(start_date)) & (master_df['Date'] <= pd.to_datetime(end_date))
            final_df = master_df.loc[mask].copy()

            final_df = metrics.apply_slippage(final_df, slippage)

            # CALCULATE LEADERBOARD
            leaderboard_df = get_cached_leaderboard(all_dfs, used_files, start_date, end_date, investment, rf_rate, slippage)

            if not leaderboard_df.empty:
                cols = ['Strategy', 'Net Profit', 'ROI %', 'Profit/Trade', 'Sharpe', 'Sortino', 'Calmar', 'Omega',
                        'Tail Ratio',
                        'Profit Factor', 'Risk:Reward', 'Win Rate %', 'Max DD %', 'Trades', 'Trades/Year']
                # Safety check
                for c in ['Calmar', 'Omega', 'Tail Ratio']:
                    if c not in leaderboard_df.columns: leaderboard_df[c] = 0.0
                leaderboard_df = leaderboard_df[cols].sort_values(by="Sharpe", ascending=False)

            st.sidebar.info(f"Showing: {start_date.strftime('%b %Y')} to {end_date.strftime('%b %Y')}")
        else:
            final_df = pd.DataFrame()
            leaderboard_df = pd.DataFrame()
    else:
        final_df = pd.DataFrame()
        leaderboard_df = pd.DataFrame()

    if used_files:
        with st.sidebar.expander(f"📂 Active Files ({len(used_files)})", expanded=False):
            for f in used_files: st.write(f"✅ {f}")

    if not final_df.empty:
        st.sidebar.markdown("---")
        st.sidebar.subheader("💾 Export Results")
        csv = final_df.to_csv(index=False).encode('utf-8')
        st.sidebar.download_button("Download Filtered CSV", data=csv, file_name="Trade_Analysis_Filtered.csv",
                                   mime="text/csv")

    # --- METRICS & TABS ---
    if not final_df.empty:
        # Main Metrics Calculation
        total_profit = final_df['Net P&L'].sum()
        final_equity = investment + total_profit

        if use_compound:
            days_passed = (final_df['Date'].max() - final_df['Date'].min()).days
            years_passed = days_passed / 365.25 if days_passed > 0 else 1
            if final_equity > 0:
                cagr = ((final_equity / investment) ** (1 / years_passed)) - 1
                roi_display = cagr * 100
                roi_label = "🚀 CAGR (Ann. Growth)"
            else:
                roi_display = -100
                roi_label = "🚀 CAGR (Busted)"
        else:
            roi_display = (total_profit / investment) * 100
            roi_label = "🚀 Total ROI (Simple)"

        cum_pnl = final_df['Net P&L'].cumsum()
        peak = (investment + cum_pnl).cummax()
        dd = (investment + cum_pnl) - peak
        dd_pct = (dd / peak) * 100
        max_dd = dd_pct.min()

        win_rate = (len(final_df[final_df['Net P&L'] > 0]) / len(final_df)) * 100
        final_df['Drawdown %'] = dd_pct
        combined_duration = metrics.calculate_drawdown_duration(final_df)

        daily_df = final_df.set_index('Date')['Net P&L'].resample('D').sum().fillna(0)
        daily_rets = daily_df / investment
        daily_rf = (rf_rate / 100) / 252

        daily_excess_rets = daily_rets - daily_rf
        daily_sharpe = (daily_excess_rets.mean() / daily_rets.std()) * np.sqrt(252) if daily_rets.std() != 0 else 0

        neg_excess_rets = daily_rets[daily_rets < daily_rf] - daily_rf
        downside_dev = np.sqrt((neg_excess_rets ** 2).mean())
        daily_sortino = (daily_excess_rets.mean() / downside_dev) * np.sqrt(252) if downside_dev != 0 else 0

        gains = daily_rets[daily_rets > 0].sum()
        losses = abs(daily_rets[daily_rets < 0].sum())
        omega = gains / losses if losses != 0 else 0

        gross_profit = final_df[final_df['Net P&L'] > 0]['Net P&L'].sum()
        gross_loss = abs(final_df[final_df['Net P&L'] < 0]['Net P&L'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else 0

        avg_win = final_df[final_df['Net P&L'] > 0]['Net P&L'].mean()
        avg_loss = abs(final_df[final_df['Net P&L'] < 0]['Net P&L'].mean())
        rr_ratio = avg_win / avg_loss if avg_loss != 0 else 0

        # Display Top Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Net Profit", f"₹{total_profit:,.0f}")
        c2.metric(roi_label, f"{roi_display:,.1f}%")
        c3.metric("📉 Max Drawdown", f"{max_dd:.2f}%")
        c4.metric("⏳ Max Duration", f"{combined_duration} Days")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("⚡ Daily Sharpe", f"{daily_sharpe:.2f}")
        c6.metric("🛡️ Daily Sortino", f"{daily_sortino:.2f}")
        c7.metric("Ω Omega Ratio", f"{omega:.2f}", help=">1.5 is excellent.")
        c8.metric("⚖️ Profit Factor", f"{profit_factor:.2f}")

        c9, c10, c11, c12 = st.columns(4)
        c9.metric("🔼 Avg Win", f"₹{avg_win:,.0f}")
        c10.metric("🔽 Avg Loss", f"₹{avg_loss:,.0f}")
        c11.metric("⚖️ Risk:Reward", f"1:{rr_ratio:.2f}")
        c12.metric("📊 Total Trades", f"{len(final_df)}")

        st.markdown("---")

        # TABS
        tab_lb, tab1, tab2, t_tsl, tab3, tab4, tab_comp, tab5 = st.tabs(
            ["🏆 Leaderboard", "📈 Interactive Charts", "🔥 P&L Heatmap", "🛡️ Trade Analysis (Stops & Losses)",
             "🎲 Monte Carlo", "📅 Seasonality",
             "💸 Compounding", "📋 Detailed Data"])

        with tab_lb:
            st.markdown("### 🏆 Strategy Performance Ranking")
            if not leaderboard_df.empty:
                def highlight_max(s):
                    is_max = s == s.max()
                    return ['background-color: #dcfce7; color: #166534; font-weight: bold' if v else '' for v in is_max]

                st.dataframe(
                    leaderboard_df.style.format({
                        'Net Profit': "₹{:,.0f}", 'ROI %': "{:,.1f}%", 'Profit/Trade': "₹{:,.0f}",
                        'Sharpe': "{:.2f}", 'Sortino': "{:.2f}", 'Calmar': "{:.2f}", 'Omega': "{:.2f}",
                        'Tail Ratio': "{:.2f}",
                        'Profit Factor': "{:.2f}", 'Risk:Reward': "{:.2f}", 'Win Rate %': "{:.1f}%",
                        'Max DD %': "{:.2f}%", 'Trades/Year': "{:,.0f}"
                    }).apply(highlight_max, subset=['Net Profit', 'ROI %', 'Sharpe', 'Omega', 'Calmar']),
                    width="stretch", height=500
                )
            else:
                st.warning("Not enough data to generate leaderboard.")

        with tab1:
            fig = charts.plot_equity_and_drawdown(final_df)
            st.plotly_chart(fig, width="stretch")

            st.markdown("### 🎢 Rolling Sortino Ratio")
            roll_window = st.slider("Rolling Window (Days)", 30, 365, 90)
            rolling_sortino = metrics.calculate_rolling_sortino(final_df, window_days=roll_window, rf_rate=rf_rate)
            fig_roll = charts.plot_rolling_sortino(rolling_sortino, roll_window)
            st.plotly_chart(fig_roll, width="stretch")

            fig_dist = charts.plot_pnl_distribution(final_df)
            st.plotly_chart(fig_dist, width="stretch")

        with tab2:
            matrix_df = metrics.create_matrix(final_df, investment)
            visual_df = matrix_df.drop(index='Grand Total', errors='ignore')
            
            # Prepare data for heatmap helper
            heatmap_data = visual_df.drop(columns=['Yearly Total', 'Yearly Return (%)'], errors='ignore')
            total_data = visual_df[['Yearly Total']]
            roi_data = visual_df[['Yearly Return (%)']]
            
            st.markdown("### 📋 Monthly P&L Heatmap")
            fig_heat = charts.plot_heatmap(heatmap_data, total_data, roi_data)
            st.plotly_chart(fig_heat, width="stretch")

        with t_tsl:
            st.markdown("### 🛡️ Trade Analysis (Missed Wins & Realized Losses)")

            # --- 1. RUN-UP ANALYSIS ---
            st.subheader("1. Missed Opportunities (Run-up Analysis)")
            st.caption("Losing trades that were profitable at one point. Could a Trailing SL have saved them?")

            if master_df['Run-up'].sum() == 0:
                st.warning("⚠️ No 'Run-up' or 'MFE' column detected. Cannot analyze missed opportunities.")
            else:
                c_runup_metrics, c_runup_chart = st.columns([1, 2])
                analysis_df, losers_df = metrics.calculate_trailing_sl_analysis(master_df)

                with c_runup_metrics:
                    total_missed = analysis_df['Trades Count'].sum()
                    st.metric("Total 'Missed' Trades", f"{total_missed}",
                              help="Losing trades that reached at least ₹3,000 profit.")
                    st.dataframe(analysis_df.style.background_gradient(subset=['Trades Count'], cmap="Oranges"),
                                 width="stretch")

                with c_runup_chart:
                    fig_tsl = charts.plot_trailing_sl_analysis(analysis_df)
                    if fig_tsl:
                        st.plotly_chart(fig_tsl, width="stretch")

            st.markdown("---")

            # --- 2. REALIZED LOSS ANALYSIS ---
            st.subheader("2. Realized Loss Distribution")
            st.caption("How bad are your losses? Are they small cuts or massive blowouts?")

            loss_dist_df = metrics.calculate_loss_breakdown(master_df)

            if not loss_dist_df.empty:
                c_loss_metrics, c_loss_chart = st.columns([1, 2])

                with c_loss_metrics:
                    total_losses = len(master_df[master_df['Net P&L'] < 0])
                    avg_loss_val = master_df[master_df['Net P&L'] < 0]['Net P&L'].mean()
                    st.metric("Total Losing Trades", f"{total_losses}", delta=f"Avg Loss: ₹{avg_loss_val:,.0f}",
                              delta_color="inverse")
                    st.dataframe(
                        loss_dist_df.style.format({"Total Loss": "₹{:,.0f}"}).background_gradient(subset=['Count'],
                                                                                                  cmap="Reds"),
                        width="stretch")

                with c_loss_chart:
                    fig_loss = charts.plot_loss_breakdown(loss_dist_df)
                    if fig_loss:
                        st.plotly_chart(fig_loss, width="stretch")
            else:
                st.info("No losing trades found to analyze.")

        with tab3:
            st.markdown("### 🎲 Monte Carlo Simulation")
            simulations = 50
            fig_mc, expected_outcome = charts.plot_monte_carlo(final_df['Net P&L'], simulations=simulations)
            st.plotly_chart(fig_mc, width="stretch")
            st.metric("Expected Outcome", f"₹{expected_outcome:,.0f}")

        with tab4:
            st.markdown("### 📅 Behavioral Analysis")
            col_day, col_mon = st.columns(2)
            fig_day, fig_mon = charts.plot_seasonality(final_df)
            col_day.plotly_chart(fig_day, width="stretch")
            col_mon.plotly_chart(fig_mon, width="stretch")

        with tab_comp:
            st.markdown("### 💸 Compounding Simulation")
            mode = st.radio("Scaling:", ("Linear (+1x per Year)", "Proportional (Reinvest Profits)"))
            code = "linear" if "Linear" in mode else "proportional"
            comp_df = metrics.calculate_compounding_simulation(final_df, investment, mode=code, tax_rate=tax_rate)

            fig_c = charts.plot_compounding(comp_df)
            st.plotly_chart(fig_c, width="stretch")
            st.dataframe(comp_df.style.format(
                {"Start Balance": "₹{:,.0f}", "End Balance": "₹{:,.0f}", "Raw Profit": "₹{:,.0f}",
                 "Net Profit": "₹{:,.0f}", "Yearly Growth %": "{:.1f}%"}), width="stretch")

        with tab5:
            st.markdown("### 📋 Monthly P&L Matrix")
            matrix_display = metrics.create_matrix(final_df, investment)
            st.dataframe(matrix_display.style.format("{:,.0f}").map(charts.color_surplus_deficit), width="stretch", height=800)

else:
    if 'available_files' in locals() and available_files: 
        st.info("👈 Please select at least one file from the sidebar to begin analysis.")
