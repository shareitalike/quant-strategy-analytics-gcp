"""
metrics.py

This module contains all quantitative financial calculations and simulations.
It is a pure logic layer with no dependencies on the UI (Streamlit) or visualization libraries.
"""

import pandas as pd
import numpy as np

# --- HELPER: CALCULATE DRAWDOWN DURATION ---
def calculate_drawdown_duration(df):
    """
    Calculates the maximum duration (in days) the strategy was in a drawdown.

    Args:
        df (pd.DataFrame): DataFrame containing 'Date' and 'Drawdown %' columns.

    Returns:
        int: The maximum number of days spent in a continuous drawdown.
    """
    if df.empty: return 0
    df = df.reset_index(drop=True)

    is_underwater = df['Drawdown %'] < 0
    if not is_underwater.any(): return 0

    drawdown_periods = (is_underwater != is_underwater.shift()).cumsum()
    underwater_groups = df[is_underwater].groupby(drawdown_periods)

    max_duration = 0
    for _, group in underwater_groups:
        start_date = group['Date'].min()
        end_date = group['Date'].max()
        duration = (end_date - start_date).days
        if duration > max_duration:
            max_duration = duration
    return max_duration


# --- HELPER: ROLLING SORTINO ---
def calculate_rolling_sortino(df, window_days=90, rf_rate=0.0):
    """
    Calculates the rolling Sortino Ratio over a specified window.

    Args:
        df (pd.DataFrame): DataFrame with 'Date' and 'Net P&L'.
        window_days (int): The rolling window size in days.
        rf_rate (float): Risk-free rate (annual %).

    Returns:
        pd.Series: A timeseries of the rolling Sortino Ratio.
    """
    daily_pnl = df.set_index('Date')['Net P&L'].resample('D').sum().fillna(0)
    daily_rets = daily_pnl

    rolling_mean = daily_rets.rolling(window=window_days).mean()
    neg_rets = daily_rets.copy()
    neg_rets[neg_rets > 0] = 0
    rolling_downside = np.sqrt((neg_rets ** 2).rolling(window=window_days).mean())
    rolling_sortino = (rolling_mean / rolling_downside.replace(0, np.nan)) * np.sqrt(252)
    return rolling_sortino


# --- HELPER: APPLY SLIPPAGE ---
def apply_slippage(df, slippage_per_trade):
    """
    Adjusts Net P&L by subtracting a fixed slippage/cost per trade.

    Args:
        df (pd.DataFrame): DataFrame with 'Net P&L'.
        slippage_per_trade (float): Cost to deduct per trade.

    Returns:
        pd.DataFrame: A new DataFrame with adjusted P&L.
    """
    if df.empty or slippage_per_trade == 0:
        return df
    df_adj = df.copy()
    df_adj['Net P&L'] = df_adj['Net P&L'] - slippage_per_trade
    return df_adj


# --- METRICS CALCULATION ---
def calculate_single_sheet_metrics(df, investment, rf_rate):
    """
    Computes a comprehensive suite of performance metrics for a single strategy.

    Args:
        df (pd.DataFrame): Strategy data with 'Date', 'Net P&L'.
        investment (float): Initial capital.
        rf_rate (float): Annual risk-free rate (%).

    Returns:
        dict: A dictionary of calculated metrics (Sharpe, Sortino, Max DD, etc.).
    """
    if df.empty: return None

    total_profit = df['Net P&L'].sum()
    roi = (total_profit / investment) * 100
    win_rate = (len(df[df['Net P&L'] > 0]) / len(df)) * 100 if len(df) > 0 else 0

    cum_pnl = df['Net P&L'].cumsum()
    peak = (investment + cum_pnl).cummax()
    dd = (investment + cum_pnl) - peak
    dd_pct = (dd / peak) * 100
    max_dd = dd_pct.min() # usually negative

    avg_pnl_per_trade = total_profit / len(df) if len(df) > 0 else 0

    date_diff = df['Date'].max() - df['Date'].min()
    days_active = date_diff.days
    years_active = days_active / 365.25
    if years_active > 0:
        trades_per_year = len(df) / years_active
    else:
        trades_per_year = len(df)

    daily_df = df.set_index('Date')['Net P&L'].resample('D').sum().fillna(0)
    daily_rets = daily_df / investment
    daily_rf = (rf_rate / 100) / 252

    daily_excess_rets = daily_rets - daily_rf
    daily_std = daily_rets.std()
    sharpe = (daily_excess_rets.mean() / daily_std) * np.sqrt(252) if daily_std != 0 else 0

    neg_excess_rets = daily_rets[daily_rets < daily_rf] - daily_rf
    downside_dev = np.sqrt((neg_excess_rets ** 2).mean())
    sortino = (daily_excess_rets.mean() / downside_dev) * np.sqrt(252) if downside_dev != 0 else 0

    gains = daily_rets[daily_rets > 0].sum()
    losses = abs(daily_rets[daily_rets < 0].sum())
    omega = gains / losses if losses != 0 else 0

    p95 = daily_rets.quantile(0.95)
    p05 = abs(daily_rets.quantile(0.05))
    tail_ratio = p95 / p05 if p05 != 0 else 0

    gross_profit = df[df['Net P&L'] > 0]['Net P&L'].sum()
    gross_loss = abs(df[df['Net P&L'] < 0]['Net P&L'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else 0

    avg_win = df[df['Net P&L'] > 0]['Net P&L'].mean()
    avg_loss = abs(df[df['Net P&L'] < 0]['Net P&L'].mean())
    rr_ratio = avg_win / avg_loss if avg_loss != 0 else 0

    # --- CALMAR RATIO CALCULATION ---
    if years_active > 0:
        annual_return_pct = (total_profit / investment) / years_active * 100
    else:
        annual_return_pct = 0

    # Max DD is usually negative, so we take absolute value
    if max_dd != 0:
        calmar = abs(annual_return_pct / max_dd)
    else:
        calmar = 0

    return {
        "Net Profit": total_profit, "ROI %": roi, "Profit/Trade": avg_pnl_per_trade,
        "Sharpe": sharpe, "Sortino": sortino, "Calmar": calmar,
        "Omega": omega, "Tail Ratio": tail_ratio,
        "Profit Factor": profit_factor, "Risk:Reward": rr_ratio, "Win Rate %": win_rate,
        "Max DD %": max_dd, "Trades": len(df), "Trades/Year": trades_per_year
    }


def calculate_compounding_simulation(df, initial_capital, mode="linear", tax_rate=0.0):
    """
    Simulates portfolio growth processing yearly compounded returns or linear growth.

    Args:
        df: DataFrame with Date and Net P&L.
        initial_capital: Starting money.
        mode: "linear" or "proportional".
        tax_rate: Percentage to deduct from profits annually.

    Returns:
        pd.DataFrame: Simulation results by year.
    """
    yearly_groups = df.groupby('Year')['Net P&L'].sum()
    simulation_data = []
    current_equity = initial_capital
    linear_equity = initial_capital
    years_list = sorted(yearly_groups.index.unique())

    for i, year in enumerate(years_list):
        raw_profit = yearly_groups[year]
        if mode == "linear":
            scaling_factor = 1.0 + i
        else:
            scaling_factor = current_equity / initial_capital
            if scaling_factor < 0.1: scaling_factor = 0.1

        gross_compounded_profit = raw_profit * scaling_factor
        tax_deduction = 0
        if gross_compounded_profit > 0:
            tax_deduction = gross_compounded_profit * (tax_rate / 100)

        net_compounded_profit = gross_compounded_profit - tax_deduction
        start_bal = current_equity
        end_bal = start_bal + net_compounded_profit
        yearly_growth_pct = (net_compounded_profit / start_bal * 100) if start_bal > 0 else 0
        linear_equity += raw_profit

        simulation_data.append({
            "Year": year, "Start Balance": start_bal, "Scaling Factor": f"{scaling_factor:.2f}x",
            "Raw Profit": raw_profit, "Tax/Fee": tax_deduction, "Net Profit": net_compounded_profit,
            "End Balance": end_bal, "Yearly Growth %": yearly_growth_pct, "Linear Equity (Ref)": linear_equity
        })
        current_equity = end_bal

    return pd.DataFrame(simulation_data)


def calculate_trailing_sl_analysis(df):
    """
    Analyzes Trade Run-ups (MFE) to determine potential missed profits.

    Args:
        df: DataFrame with 'Net P&L' and 'Run-up'.

    Returns:
        tuple: (Summary DataFrame, Detailed Losing Trades DataFrame)
    """
    losing_trades = df[df['Net P&L'] < 0].copy()

    if losing_trades.empty or 'Run-up' not in df.columns or df['Run-up'].sum() == 0:
        return None, pd.DataFrame()

    buckets = [
        (3000, 5000, "3k - 5k"),
        (5000, 8000, "5k - 8k"),
        (8000, 12000, "8k - 12k"),
        (12000, 20000, "12k - 20k"),
        (20000, float('inf'), "> 20k")
    ]

    results = []

    for b_min, b_max, label in buckets:
        subset = losing_trades[(losing_trades['Run-up'] >= b_min) & (losing_trades['Run-up'] < b_max)]
        count = len(subset)
        avg_loss = subset['Net P&L'].mean() if count > 0 else 0

        results.append({
            'Run-up Range': label,
            'Trades Count': count,
            'Avg Realized Loss': avg_loss
        })

    return pd.DataFrame(results), losing_trades


def calculate_loss_breakdown(df):
    """
    Categories realized losses by magnitude.

    Args:
        df: DataFrame with Net P&L.

    Returns:
        pd.DataFrame: Breakdown of losses by severity.
    """
    losing_trades = df[df['Net P&L'] < 0].copy()
    if losing_trades.empty: return pd.DataFrame()

    # We use abs() for easier comparison, but remember P&L is negative
    # 0-3k, 3k-5k, 5k-10k, >10k
    b1 = losing_trades[(losing_trades['Net P&L'] < 0) & (losing_trades['Net P&L'] >= -3000)]  # 0 to -3k
    b2 = losing_trades[(losing_trades['Net P&L'] < -3000) & (losing_trades['Net P&L'] >= -5000)]  # -3k to -5k
    b3 = losing_trades[(losing_trades['Net P&L'] < -5000) & (losing_trades['Net P&L'] >= -10000)]  # -5k to -10k
    b4 = losing_trades[losing_trades['Net P&L'] < -10000]  # < -10k

    data = [
        {"Loss Severity": "Small (0 - 3k)", "Count": len(b1), "Total Loss": b1['Net P&L'].sum()},
        {"Loss Severity": "Medium (3k - 5k)", "Count": len(b2), "Total Loss": b2['Net P&L'].sum()},
        {"Loss Severity": "Large (5k - 10k)", "Count": len(b3), "Total Loss": b3['Net P&L'].sum()},
        {"Loss Severity": "Massive (> 10k)", "Count": len(b4), "Total Loss": b4['Net P&L'].sum()},
    ]
    return pd.DataFrame(data)


def create_matrix(df, investment):
    """
    Creates a Month vs Year P&L Matrix.

    Args:
        df: DataFrame with Date, Year, Month, Net P&L.
        investment: Initial Capital.

    Returns:
        pd.DataFrame: Pivot table of monthly returns.
    """
    matrix = df.groupby(['Year', 'Month'], observed=False)['Net P&L'].sum().reset_index()

    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    matrix['Month'] = pd.Categorical(matrix['Month'], categories=months, ordered=True)
    pivot = matrix.pivot(index='Year', columns='Month', values='Net P&L').fillna(0)

    pivot['Yearly Total'] = pivot.sum(axis=1)
    pivot['Yearly Return (%)'] = (pivot['Yearly Total'] / investment) * 100

    grand_total = pivot.sum(axis=0)
    grand_total['Yearly Return (%)'] = (grand_total['Yearly Total'] / investment) * 100

    pivot.index = pivot.index.astype(str)
    pivot.loc['Grand Total'] = grand_total

    return pivot


def get_optimized_leaderboard(all_dfs, file_names, start_date, end_date, investment, rf_rate, slippage):
    """
    Generates a leaderboard of all strategies filtered by the selected date range.

    Args:
        all_dfs: List of DataFrames.
        file_names: List of filenames corresponding to dfs.
        start_date: Start datetime filter.
        end_date: End datetime filter.
        investment: Initial capital.
        rf_rate: Risk free rate.
        slippage: Transaction cost per trade.

    Returns:
        pd.DataFrame: Comparative metrics for all strategies.
    """
    data = []
    for name, df_raw in zip(file_names, all_dfs):
        d_mask = (df_raw['Date'] >= pd.to_datetime(start_date)) & (df_raw['Date'] <= pd.to_datetime(end_date))
        df_filtered = df_raw.loc[d_mask].copy()
        df_filtered = apply_slippage(df_filtered, slippage)

        metrics = calculate_single_sheet_metrics(df_filtered, investment, rf_rate)
        if metrics:
            metrics['Strategy'] = name.replace(".xlsx", "")
            data.append(metrics)
    return pd.DataFrame(data)
