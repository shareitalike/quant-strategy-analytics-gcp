"""
charts.py

This module handles all visualization and charting logic.
It uses Plotly to generate interactive charts and provides styling helpers.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd

def color_surplus_deficit(val):
    """
    Pandas Styler background gradient helper for Matrix.
    """
    if isinstance(val, (int, float)):
        if val > 0:
            return 'color: #15803d; font-weight: bold;'  # Vivid Green
        elif val < 0:
            return 'color: #b91c1c; font-weight: bold;'  # Vivid Red
        else:
            return 'color: #94a3b8;'  # Slate
    return ''

def plot_equity_and_drawdown(df):
    """
    Creates a combined Equity Curve and Drawdown chart.
    Optimizes large datasets by downsampling if needed.
    """
    df['Cumulative'] = df['Net P&L'].cumsum()
    plot_df = df.copy()
    
    # Simple Downsampling for performance
    if len(plot_df) > 5000:
        factor = len(plot_df) // 2000
        plot_df = plot_df.iloc[::factor]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.70, 0.30],
                        subplot_titles=("Equity Curve", "Drawdown"))
    
    fig.add_trace(go.Scatter(x=plot_df['Date'], y=plot_df['Cumulative'],
                             name='Equity', line=dict(color='#16a34a', width=2),
                             fill='tozeroy', fillcolor='rgba(22, 163, 74, 0.1)'), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=plot_df['Date'], y=plot_df['Drawdown %'],
                             name='Drawdown', line=dict(color='#dc2626', width=1),
                             fill='tozeroy', fillcolor='rgba(220, 38, 38, 0.2)'), row=2, col=1)
    
    fig.update_layout(height=700, template='plotly_white', hovermode='x unified', margin=dict(t=40))
    return fig

def plot_rolling_sortino(sortino_series, window):
    """
    Plots the rolling Sortino Ratio.
    """
    fig_roll = go.Figure()
    fig_roll.add_trace(go.Scatter(x=sortino_series.index, y=sortino_series, mode='lines',
                                  name=f'{window}-Day Sortino', line=dict(color='#8b5cf6', width=2)))
    fig_roll.add_hline(y=0, line_dash="dash", line_color="gray")
    fig_roll.add_hline(y=2, line_dash="dot", line_color="green", annotation_text="Excellent (>2.0)")
    fig_roll.update_layout(title=f"Rolling Sortino", yaxis_title="Sortino", height=400, template="plotly_white")
    return fig_roll

def plot_pnl_distribution(df):
    """
    Plots histogram of P&L distribution.
    """
    fig_dist = px.histogram(df, x="Net P&L", nbins=50, title="P&L Distribution",
                            color_discrete_sequence=['#2563EB'], marginal="box")
    return fig_dist

def plot_heatmap(heatmap_df, total_df, roi_df):
    """
    Creates the Heatmap visualization (Monthly P&L, Total, ROI).
    
    Args:
        heatmap_df (pd.DataFrame): Monthly P&L Data.
        total_df (pd.DataFrame): 'Yearly Total' column data.
        roi_df (pd.DataFrame): 'Yearly Return (%)' column data.
    """
    custom_scale = [[0.0, "#b91c1c"], [0.499, "#fca5a5"], [0.5, "#ffffff"], [0.501, "#86efac"],
                    [1.0, "#15803d"]]
    
    # Determine scale range dynamically
    all_values = heatmap_df.values.flatten()
    # Filter out NaNs if any
    all_values = all_values[~np.isnan(all_values)]
    
    if len(all_values) > 0:
        max_pnl = max(abs(all_values.min()), abs(all_values.max()))
    else:
        max_pnl = 1000

    fig_heat = make_subplots(rows=1, cols=3, shared_yaxes=True, column_widths=[0.8, 0.1, 0.1],
                             horizontal_spacing=0.02)
    
    fig_heat.add_trace(
        go.Heatmap(z=heatmap_data_values(heatmap_df), x=heatmap_df.columns, y=heatmap_df.index, colorscale=custom_scale,
                   zmin=-max_pnl, zmax=max_pnl, text=heatmap_data_values(heatmap_df), texttemplate="%{text:,.0f}",
                   showscale=False), row=1, col=1)
    
    fig_heat.add_trace(
        go.Heatmap(z=total_df.values, x=['Total'], y=total_df.index, colorscale=custom_scale, zmin=-max_pnl,
                   zmax=max_pnl, text=total_df.values, texttemplate="%{text:,.0f}", showscale=False), row=1,
        col=2)
    
    fig_heat.add_trace(
        go.Heatmap(z=roi_df.values, x=['ROI %'], y=roi_df.index, colorscale=custom_scale, zmin=-100,
                   zmax=100, text=roi_df.values, texttemplate="%{text:.1f}%",
                   showscale=False), row=1, col=3)
    
    fig_heat.update_layout(height=800, template='plotly_white')
    return fig_heat

def heatmap_data_values(df):
    return df.values

def plot_trailing_sl_analysis(analysis_df):
    """
    Plots the Run-up / Missed Opportunities bar chart.
    """
    if analysis_df.empty:
        return None
        
    fig_tsl = px.bar(analysis_df, x='Run-up Range', y='Trades Count',
                     title="Losing Trades by Max Profit Reached",
                     color='Trades Count', color_continuous_scale='Oranges', text='Trades Count')
    fig_tsl.update_layout(template='plotly_white')
    return fig_tsl

def plot_loss_breakdown(loss_dist_df):
    """
    Plots the Realized Loss Distribution bar chart.
    """
    if loss_dist_df.empty:
        return None
        
    fig_loss = px.bar(loss_dist_df, x='Loss Severity', y='Count',
                      title="Count of Trades by Realized Loss Amount",
                      color='Count', color_continuous_scale='Reds', text='Count')
    fig_loss.update_layout(template='plotly_white')
    return fig_loss

def plot_monte_carlo(original_pnl, simulations=50):
    """
    Plots Monte Carlo paths.
    """
    pnl_array = original_pnl.values.copy()
    fig_mc = go.Figure()
    
    # Original cumulative path
    fig_mc.add_trace(go.Scatter(y=np.cumsum(pnl_array), mode='lines', name='Original',
                                line=dict(color='blue', width=3)))
    
    final_vals = []
    for i in range(simulations):
        np.random.shuffle(pnl_array)
        sim_curve = np.cumsum(pnl_array)
        final_vals.append(sim_curve[-1])
        fig_mc.add_trace(go.Scatter(y=sim_curve, mode='lines', line=dict(color='gray', width=1), opacity=0.1,
                                    showlegend=False))
            
    fig_mc.update_layout(height=600, template='plotly_white', title="Monte Carlo Paths")
    return fig_mc, np.mean(final_vals)

def plot_seasonality(df):
    """
    Plots Average P&L by Day and Month.
    """
    # Day Stats
    day_stats = df.groupby('Day', observed=False)['Net P&L'].mean().reindex(
        ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']).fillna(0)
    fig_day = px.bar(day_stats, title="Avg P&L by Day", color=day_stats.values, color_continuous_scale="RdYlGn")
    
    # Month Stats
    mon_stats = df.groupby('Month', observed=False)['Net P&L'].mean().reindex(
        ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
         'November', 'December']).fillna(0)
    fig_mon = px.bar(mon_stats, title="Avg P&L by Month", color=mon_stats.values,
                     color_continuous_scale="RdYlGn")
    
    return fig_day, fig_mon

def plot_compounding(comp_df):
    """
    Plots Compounding vs Linear Growth projection.
    """
    fig_c = go.Figure()
    fig_c.add_trace(go.Scatter(x=comp_df['Year'], y=comp_df['End Balance'], name="Compounded",
                               line=dict(color='#16a34a', width=3)))
    fig_c.add_trace(go.Scatter(x=comp_df['Year'], y=comp_df['Linear Equity (Ref)'], name="Linear",
                               line=dict(color='#6b7280', width=2, dash='dash')))
    fig_c.update_layout(height=400, template='plotly_white', title="Growth Projection")
    return fig_c
