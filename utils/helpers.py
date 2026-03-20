import pandas as pd
import plotly.graph_objects as go
import numpy as np

def process_option_data(response):
    """Parse Dhan option chain response, return (DataFrame, spot_price)"""
    if not response or "data" not in response:
        return pd.DataFrame(), 0
    data = response["data"]
    spot = data.get("last_price", 0)
    oc = data.get("oc", {})
    rows = []
    for strike_str, options in oc.items():
        strike = float(strike_str)
        ce = options.get("ce", {})
        pe = options.get("pe", {})
        rows.append({
            "Strike": strike,
            "Call OI": ce.get("oi", 0),
            "Call LTP": ce.get("last_price", 0),
            "Call IV": ce.get("implied_volatility", 0),
            "Call Delta": ce.get("greeks", {}).get("delta", 0),
            "Call Gamma": ce.get("greeks", {}).get("gamma", 0),
            "Put OI": pe.get("oi", 0),
            "Put LTP": pe.get("last_price", 0),
            "Put IV": pe.get("implied_volatility", 0),
            "Put Delta": pe.get("greeks", {}).get("delta", 0),
            "Put Gamma": pe.get("greeks", {}).get("gamma", 0),
        })
    df = pd.DataFrame(rows).sort_values("Strike").reset_index(drop=True)
    return df, spot

def calculate_pcr(df):
    """Put‑Call Ratio based on total OI"""
    if df.empty:
        return 0
    total_call_oi = df["Call OI"].sum()
    total_put_oi = df["Put OI"].sum()
    return total_put_oi / total_call_oi if total_call_oi != 0 else 0

def get_support_resistance(df):
    """Support = max Put OI strike, Resistance = max Call OI strike"""
    if df.empty:
        return 0, 0
    support = df.loc[df["Put OI"].idxmax(), "Strike"]
    resistance = df.loc[df["Call OI"].idxmax(), "Strike"]
    return support, resistance

def get_atm_strike(df, spot):
    """Find strike closest to spot price"""
    if df.empty:
        return 0
    return df.iloc[(df["Strike"] - spot).abs().argsort()[:1]]["Strike"].values[0]

def get_signal(pcr):
    if pcr < 0.8:
        return "🟢 Bullish – Consider Call"
    elif pcr > 1.2:
        return "🔴 Bearish – Consider Put"
    else:
        return "🟡 Neutral – Wait"

def plot_oi_heatmap(df):
    """Placeholder – implement with Plotly Heatmap if needed"""
    fig = go.Figure()
    fig.add_annotation(text="OI Heatmap (to be implemented)", x=0.5, y=0.5, showarrow=False)
    return fig

def plot_payoff(atm):
    """Placeholder – generate payoff diagram for ATM straddle"""
    fig = go.Figure()
    fig.add_annotation(text=f"Payoff diagram for ATM = {atm}", x=0.5, y=0.5, showarrow=False)
    return fig
