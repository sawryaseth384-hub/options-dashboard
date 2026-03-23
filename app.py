import sys
import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain

# =============================================================================
# CONFIGURATION
# =============================================================================
st.set_page_config(page_title="🧠 Smart Money Options Dashboard", layout="wide")
st.title("🧠 Smart Money Options Dashboard - Institutional Grade")

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
if "previous_data" not in st.session_state:
    st.session_state.previous_data = None

# =============================================================================
# DATA FETCHING FUNCTIONS (CACHED)
# =============================================================================
@st.cache_data(ttl=3600)
def fetch_expiry(sec_id):
    """Fetch expiry list for a given security ID."""
    data = get_expiry(sec_id)
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "data" in data:
        return data["data"]
    return []

@st.cache_data(ttl=300)
def fetch_chain(sec_id, exp):
    """Fetch option chain data for given security ID and expiry."""
    data = get_option_chain(sec_id, exp)
    if not data or "data" not in data:
        return {}
    inner = data["data"]
    if isinstance(inner, dict) and "data" in inner:
        inner = inner["data"]
    return inner

# =============================================================================
# DATA PROCESSING FUNCTIONS
# =============================================================================
def process_option_chain(raw_data):
    """Convert raw option chain to DataFrame with required columns."""
    spot = raw_data.get("last_price", 0)
    oc = raw_data.get("oc", {})
    rows = []
    for strike, val in oc.items():
        ce = val.get("ce", {})
        pe = val.get("pe", {})
        rows.append({
            "Strike": int(float(strike)),
            "CE OI": ce.get("oi", 0),
            "CE LTP": ce.get("last_price", 0),
            "CE Delta": ce.get("greeks", {}).get("delta", 0),
            "CE Gamma": ce.get("greeks", {}).get("gamma", 0),
            "CE Theta": ce.get("greeks", {}).get("theta", 0),
            "CE Vega": ce.get("greeks", {}).get("vega", 0),
            "CE Volume": ce.get("volume", 0),  # if available
            "PE OI": pe.get("oi", 0),
            "PE LTP": pe.get("last_price", 0),
            "PE Delta": pe.get("greeks", {}).get("delta", 0),
            "PE Gamma": pe.get("greeks", {}).get("gamma", 0),
            "PE Theta": pe.get("greeks", {}).get("theta", 0),
            "PE Vega": pe.get("greeks", {}).get("vega", 0),
            "PE Volume": pe.get("volume", 0),
        })
    df = pd.DataFrame(rows).sort_values("Strike")
    return df, spot

def add_oi_change(df, prev_df):
    """Add OI change columns if previous data is available."""
    if prev_df is not None:
        # Align strikes
        merged = df.merge(prev_df, on="Strike", suffixes=("", "_prev"))
        df["CE OI Change"] = merged["CE OI"] - merged["CE OI_prev"]
        df["PE OI Change"] = merged["PE OI"] - merged["PE OI_prev"]
        df["CE Price Change"] = merged["CE LTP"] - merged["CE LTP_prev"]
        df["PE Price Change"] = merged["PE LTP"] - merged["PE LTP_prev"]
        # For volume change, we might not have volume_prev, so approximate
        if "CE Volume_prev" in merged.columns:
            df["CE Volume Change"] = merged["CE Volume"] - merged["CE Volume_prev"]
            df["PE Volume Change"] = merged["PE Volume"] - merged["PE Volume_prev"]
        else:
            df["CE Volume Change"] = np.nan
            df["PE Volume Change"] = np.nan
    else:
        df["CE OI Change"] = 0
        df["PE OI Change"] = 0
        df["CE Price Change"] = 0
        df["PE Price Change"] = 0
        df["CE Volume Change"] = 0
        df["PE Volume Change"] = 0
    return df

def detect_buildup(df):
    """Classify each strike's OI change as long/short build-up or covering/unwinding."""
    def classify(row):
        # CE Buildup
        if row["CE OI Change"] > 0 and row["CE Price Change"] > 0:
            ce_type = "CE Long Build-up"
        elif row["CE OI Change"] > 0 and row["CE Price Change"] < 0:
            ce_type = "CE Short Build-up"
        elif row["CE OI Change"] < 0 and row["CE Price Change"] > 0:
            ce_type = "CE Short Covering"
        elif row["CE OI Change"] < 0 and row["CE Price Change"] < 0:
            ce_type = "CE Long Unwinding"
        else:
            ce_type = "CE Neutral"

        # PE Buildup
        if row["PE OI Change"] > 0 and row["PE Price Change"] > 0:
            pe_type = "PE Long Build-up"
        elif row["PE OI Change"] > 0 and row["PE Price Change"] < 0:
            pe_type = "PE Short Build-up"
        elif row["PE OI Change"] < 0 and row["PE Price Change"] > 0:
            pe_type = "PE Short Covering"
        elif row["PE OI Change"] < 0 and row["PE Price Change"] < 0:
            pe_type = "PE Long Unwinding"
        else:
            pe_type = "PE Neutral"

        return ce_type, pe_type

    df[["CE BuildUp", "PE BuildUp"]] = df.apply(
        lambda row: pd.Series(classify(row)), axis=1
    )
    return df

def detect_writing_vs_buying(df):
    """Detect writing (sell) vs buying based on OI change and premium change."""
    def classify(row):
        # CE
        if row["CE OI Change"] > 0 and row["CE LTP"] < row.get("CE LTP_prev", row["CE LTP"]):
            ce_action = "Writing"
        elif row["CE OI Change"] > 0 and row["CE LTP"] > row.get("CE LTP_prev", row["CE LTP"]):
            ce_action = "Buying"
        else:
            ce_action = "Neutral"
        # PE
        if row["PE OI Change"] > 0 and row["PE LTP"] < row.get("PE LTP_prev", row["PE LTP"]):
            pe_action = "Writing"
        elif row["PE OI Change"] > 0 and row["PE LTP"] > row.get("PE LTP_prev", row["PE LTP"]):
            pe_action = "Buying"
        else:
            pe_action = "Neutral"
        return ce_action, pe_action

    df[["CE Action", "PE Action"]] = df.apply(
        lambda row: pd.Series(classify(row)), axis=1
    )
    return df

def compute_total_oi(df):
    """Compute total OI for CE and PE."""
    return {
        "CE Total": df["CE OI"].sum(),
        "PE Total": df["PE OI"].sum(),
        "Overall": df["CE OI"].sum() + df["PE OI"].sum()
    }

def compute_pcr(df, atm_strike=None):
    """Compute Put-Call Ratio: overall and ATM."""
    total_ce = df["CE OI"].sum()
    total_pe = df["PE OI"].sum()
    pcr_total = total_pe / total_ce if total_ce else 0

    if atm_strike is not None:
        atm_row = df[df["Strike"] == atm_strike]
        if not atm_row.empty:
            atm_ce = atm_row["CE OI"].iloc[0]
            atm_pe = atm_row["PE OI"].iloc[0]
            pcr_atm = atm_pe / atm_ce if atm_ce else 0
        else:
            pcr_atm = np.nan
    else:
        pcr_atm = np.nan

    return pcr_total, pcr_atm

def compute_support_resistance(df, top_n=3):
    """Find support (max PE OI) and resistance (max CE OI) levels."""
    # Top N CE OI strikes (resistance)
    ce_top = df.nlargest(top_n, "CE OI")["Strike"].tolist()
    # Top N PE OI strikes (support)
    pe_top = df.nlargest(top_n, "PE OI")["Strike"].tolist()
    return ce_top, pe_top

def compute_clusters(df, threshold=0.8):
    """
    Detect OI clusters: strikes where OI is above a percentile threshold.
    Returns list of strike ranges.
    """
    ce_thresh = df["CE OI"].quantile(threshold)
    pe_thresh = df["PE OI"].quantile(threshold)
    ce_clusters = df[df["CE OI"] >= ce_thresh]["Strike"].tolist()
    pe_clusters = df[df["PE OI"] >= pe_thresh]["Strike"].tolist()
    return ce_clusters, pe_clusters

def compute_oi_walls(df):
    """
    Identify strong OI walls: strikes with highest OI concentration.
    Returns a dict with resistance wall (CE) and support wall (PE).
    """
    max_ce = df.loc[df["CE OI"].idxmax(), "Strike"]
    max_pe = df.loc[df["PE OI"].idxmax(), "Strike"]
    return {"Resistance Wall": max_ce, "Support Wall": max_pe}

def compute_max_pain(df, spot):
    """Calculate Max Pain (strike that minimizes total loss)."""
    strikes = df["Strike"].values
    pain_values = []
    for strike in strikes:
        # CE side: max(Strike - strike, 0) * CE OI
        ce_pain = ((df["Strike"] - strike).clip(lower=0) * df["CE OI"]).sum()
        # PE side: max(strike - Strike, 0) * PE OI
        pe_pain = ((strike - df["Strike"]).clip(lower=0) * df["PE OI"]).sum()
        pain_values.append((strike, ce_pain + pe_pain))
    max_pain_strike = min(pain_values, key=lambda x: x[1])[0]
    return max_pain_strike

def compute_delta_exposure(df):
    """Compute net delta exposure: CE delta * OI - PE delta * OI (approximated)."""
    df["CE Delta Exposure"] = df["CE Delta"] * df["CE OI"]
    df["PE Delta Exposure"] = -df["PE Delta"] * df["PE OI"]  # PE delta negative for put
    net_delta = df["CE Delta Exposure"].sum() + df["PE Delta Exposure"].sum()
    return net_delta

def compute_oi_velocity(df, prev_df):
    """Compute OI velocity as change per minute? Simplified: absolute change."""
    if prev_df is not None:
        df["CE OI Velocity"] = df["CE OI"] - prev_df["CE OI"]
        df["PE OI Velocity"] = df["PE OI"] - prev_df["PE OI"]
    else:
        df["CE OI Velocity"] = 0
        df["PE OI Velocity"] = 0
    return df

def detect_oi_spike(df, prev_df, threshold=2):
    """Detect OI spikes: current OI > previous OI * threshold."""
    if prev_df is not None:
        ce_spike = df["CE OI"] > (prev_df["CE OI"] * threshold)
        pe_spike = df["PE OI"] > (prev_df["PE OI"] * threshold)
    else:
        ce_spike = False
        pe_spike = False
    return ce_spike, pe_spike

def detect_traps(df, pcr, spot):
    """Detect call traps and put traps based on OI, price, and PCR."""
    # Call Trap: high CE OI but price moving up? Actually typical trap: high CE OI and price falls
    # Let's use: high CE OI near resistance + price up? We'll define as: price > ATM and CE OI high but PCR low
    max_ce_strike = df.loc[df["CE OI"].idxmax(), "Strike"]
    max_pe_strike = df.loc[df["PE OI"].idxmax(), "Strike"]
    # Call Trap condition: price above max CE OI strike and PCR < 0.7 (bullish but trapped)
    call_trap = (spot > max_ce_strike) and (pcr < 0.7)
    # Put Trap: price below max PE OI strike and PCR > 1.3 (bearish but trapped)
    put_trap = (spot < max_pe_strike) and (pcr > 1.3)
    return call_trap, put_trap

def generate_signals(df, spot, pcr_total, pcr_atm, net_delta, fii_net=0, dii_net=0):
    """
    Generate trading signals based on multiple factors.
    Returns DataFrame with signal columns.
    """
    # Basic signal: based on PCR and Delta
    df["Basic Signal"] = "Neutral"
    df["Signal Reason"] = ""

    # Strong signal: combine OI buildup, PCR, Delta, and FII
    df["Strong Signal"] = "Neutral"
    df["Strong Reason"] = ""

    # Reversal signal: OI divergence or trap conditions
    df["Reversal Signal"] = "Neutral"
    df["Reversal Reason"] = ""

    # Trap warning
    df["Trap Warning"] = "None"

    for idx, row in df.iterrows():
        # Basic Signal
        if pcr_total > 1 and row["CE Delta"] > 0.5:
            df.at[idx, "Basic Signal"] = "BUY CE"
            df.at[idx, "Signal Reason"] = "PCR bullish (>1) + high CE delta"
        elif pcr_total < 0.7 and row["PE Delta"] < -0.5:
            df.at[idx, "Basic Signal"] = "BUY PE"
            df.at[idx, "Signal Reason"] = "PCR bearish (<0.7) + high PE delta"

        # Strong Signal (confirmed by buildup and FII)
        if row["CE BuildUp"] == "CE Long Build-up" and pcr_total > 1 and row["CE Delta"] > 0.5 and fii_net > 0:
            df.at[idx, "Strong Signal"] = "STRONG BUY CE"
            df.at[idx, "Strong Reason"] = "Long build-up + Bullish PCR + High delta + FII positive"
        elif row["PE BuildUp"] == "PE Long Build-up" and pcr_total < 0.7 and row["PE Delta"] < -0.5 and fii_net < 0:
            df.at[idx, "Strong Signal"] = "STRONG BUY PE"
            df.at[idx, "Strong Reason"] = "Long build-up (PE) + Bearish PCR + High PE delta + FII negative"

        # Reversal Signal: OI divergence (price up but OI down = long unwinding)
        if row["CE BuildUp"] == "CE Long Unwinding" and row["CE Price Change"] > 0:
            df.at[idx, "Reversal Signal"] = "REVERSAL (CE unwinding)"
            df.at[idx, "Reversal Reason"] = "Price up but CE OI decreasing"
        if row["PE BuildUp"] == "PE Long Unwinding" and row["PE Price Change"] > 0:
            df.at[idx, "Reversal Signal"] = "REVERSAL (PE unwinding)"
            df.at[idx, "Reversal Reason"] = "Price up but PE OI decreasing"

        # Trap Warning
        call_trap, put_trap = detect_traps(df, pcr_total, spot)
        if call_trap:
            df.at[idx, "Trap Warning"] = "⚠️ CALL TRAP DETECTED"
        if put_trap:
            df.at[idx, "Trap Warning"] = "⚠️ PUT TRAP DETECTED"

    return df

def select_best_strike(df, spot):
    """Select best strike for trading based on delta ~0.5 and OI strength."""
    # Find strikes where delta is near 0.5 for CE and -0.5 for PE
    df["CE Delta Diff"] = abs(df["CE Delta"] - 0.5)
    df["PE Delta Diff"] = abs(df["PE Delta"] + 0.5)  # PE delta negative, so distance to -0.5
    best_ce = df.nsmallest(1, "CE Delta Diff").iloc[0]
    best_pe = df.nsmallest(1, "PE Delta Diff").iloc[0]
    # Also consider OI strength: we can combine OI rank and delta rank
    # For simplicity, we just return the strikes
    return best_ce["Strike"], best_pe["Strike"]

def add_fii_dii_placeholder():
    """Placeholder for FII/DII data. In production, fetch from API."""
    # Simulated random values for demo
    import random
    fii_net = random.randint(-5000, 5000)  # net position in crores
    dii_net = random.randint(-3000, 3000)
    return fii_net, dii_net

# =============================================================================
# UI COMPONENTS
# =============================================================================
def render_sidebar():
    """Render sidebar with controls."""
    with st.sidebar:
        st.header("🔧 Controls")
        symbol = st.text_input("Symbol", "NIFTY")
        sec_id = 13  # for NIFTY; could map symbol to ID
        expiry_list = fetch_expiry(sec_id)
        if not expiry_list:
            st.error("No expiry data")
            st.stop()
        expiry = st.selectbox("Expiry", expiry_list)
        refresh = st.button("🔄 Refresh Data")
        if refresh:
            st.cache_data.clear()
            st.rerun()
        return symbol, sec_id, expiry, refresh

def render_overview_tab(df, spot, pcr_total, pcr_atm, total_oi, max_pain, net_delta, fii_net, dii_net):
    """Render overview tab with key metrics and market bias."""
    st.header("📊 Market Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Spot Price", f"{spot:.2f}")
    col2.metric("Total PCR", f"{pcr_total:.2f}")
    col3.metric("ATM PCR", f"{pcr_atm:.2f}" if not np.isnan(pcr_atm) else "N/A")
    col4.metric("Max Pain", f"{max_pain}")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Total OI", f"{total_oi['Overall']:,.0f}")
    col6.metric("CE OI Total", f"{total_oi['CE Total']:,.0f}")
    col7.metric("PE OI Total", f"{total_oi['PE Total']:,.0f}")
    col8.metric("Net Delta Exposure", f"{net_delta:,.0f}")

    col9, col10 = st.columns(2)
    col9.metric("FII Net Position (cr)", f"{fii_net}")
    col10.metric("DII Net Position (cr)", f"{dii_net}")

    # Market bias
    if pcr_total > 1:
        st.success("📈 Market Bias: Bullish")
    elif pcr_total < 0.7:
        st.error("📉 Market Bias: Bearish")
    else:
        st.warning("⚖️ Market Bias: Sideways")

def render_oi_analysis_tab(df, prev_df):
    """Render detailed OI analysis with tables and charts."""
    st.header("🔍 OI Analysis")
    # Display OI changes and build-up
    st.subheader("Strike-wise OI & Build-up")
    display_cols = ["Strike", "CE OI", "CE OI Change", "CE BuildUp", "CE Action",
                    "PE OI", "PE OI Change", "PE BuildUp", "PE Action"]
    # Ensure columns exist
    available = [c for c in display_cols if c in df.columns]
    st.dataframe(df[available].style.format({
        "CE OI": "{:,.0f}",
        "PE OI": "{:,.0f}",
        "CE OI Change": "{:,.0f}",
        "PE OI Change": "{:,.0f}"
    }), use_container_width=True)

    # OI Clusters
    ce_clusters, pe_clusters = compute_clusters(df)
    st.info(f"📍 CE Clusters (Top 80% OI): {ce_clusters}")
    st.info(f"📍 PE Clusters (Top 80% OI): {pe_clusters}")

    # OI Walls
    walls = compute_oi_walls(df)
    st.success(f"🧱 Support Wall (Max PE OI): {walls['Support Wall']}")
    st.error(f"🧱 Resistance Wall (Max CE OI): {walls['Resistance Wall']}")

    # OI Velocity (if available)
    if "CE OI Velocity" in df.columns:
        st.subheader("OI Velocity")
        vel_df = df[["Strike", "CE OI Velocity", "PE OI Velocity"]]
        st.dataframe(vel_df.style.format("{:,.0f}"), use_container_width=True)

    # OI Spike detection
    ce_spike, pe_spike = detect_oi_spike(df, prev_df)
    if ce_spike.any():
        st.warning("⚡ CE OI Spike detected at strikes: " + ", ".join(map(str, df[ce_spike]["Strike"].tolist())))
    if pe_spike.any():
        st.warning("⚡ PE OI Spike detected at strikes: " + ", ".join(map(str, df[pe_spike]["Strike"].tolist())))

def render_support_resistance_tab(df, support, resistance, spot):
    """Render support/resistance levels and chart."""
    st.header("🛡️ Support & Resistance")
    col1, col2 = st.columns(2)
    col1.success(f"🟢 Support Levels (Max PE OI): {support}")
    col2.error(f"🔴 Resistance Levels (Max CE OI): {resistance}")

    # Show chart with S/R lines
    fig = px.bar(df, x="Strike", y=["CE OI", "PE OI"], barmode="group",
                 title="OI Profile with Support/Resistance")
    for s in support:
        fig.add_vline(x=s, line_dash="dash", line_color="green", annotation_text="Support")
    for r in resistance:
        fig.add_vline(x=r, line_dash="dash", line_color="red", annotation_text="Resistance")
    fig.add_vline(x=spot, line_dash="dot", line_color="yellow", annotation_text="Spot")
    st.plotly_chart(fig, use_container_width=True)

def render_signal_tab(df):
    """Display trading signals."""
    st.header("💡 Trading Signals")
    # Filter rows with signals
    signal_df = df[(df["Basic Signal"] != "Neutral") |
                   (df["Strong Signal"] != "Neutral") |
                   (df["Reversal Signal"] != "Neutral") |
                   (df["Trap Warning"] != "None")]
    if signal_df.empty:
        st.info("No active signals at the moment.")
    else:
        st.dataframe(signal_df[["Strike", "Basic Signal", "Signal Reason",
                                "Strong Signal", "Strong Reason",
                                "Reversal Signal", "Reversal Reason",
                                "Trap Warning"]],
                     use_container_width=True)

def render_strike_selection_tab(df, best_ce, best_pe, spot, atm_strike):
    """Display best strikes for trading."""
    st.header("🎯 Strike Selection Engine")
    col1, col2, col3 = st.columns(3)
    col1.metric("ATM Strike", f"{atm_strike}")
    col2.metric("Best CE Strike (Delta ~0.5)", f"{best_ce}")
    col3.metric("Best PE Strike (Delta ~ -0.5)", f"{best_pe}")

    # Show delta profile
    delta_fig = px.line(df, x="Strike", y=["CE Delta", "PE Delta"],
                        title="Delta Profile", markers=True)
    delta_fig.add_hline(y=0.5, line_dash="dash", line_color="green")
    delta_fig.add_hline(y=-0.5, line_dash="dash", line_color="red")
    st.plotly_chart(delta_fig, use_container_width=True)

def render_charts_tab(df, spot, support, resistance):
    """Interactive charts for OI and LTP."""
    st.header("📈 Interactive Charts")
    tab1, tab2 = st.tabs(["OI Bar Chart", "LTP Line Chart"])
    with tab1:
        fig = px.bar(df, x="Strike", y=["CE OI", "PE OI"], barmode="group",
                     title="Open Interest by Strike")
        for s in support:
            fig.add_vline(x=s, line_dash="dash", line_color="green")
        for r in resistance:
            fig.add_vline(x=r, line_dash="dash", line_color="red")
        fig.add_vline(x=spot, line_dash="dot", line_color="yellow")
        st.plotly_chart(fig, use_container_width=True)
    with tab2:
        # LTP with ATM zoom
        atm_range = st.slider("ATM Range (±)", 100, 1000, 300, key="atm_slider")
        ltp_df = df[(df["Strike"] > spot - atm_range) & (df["Strike"] < spot + atm_range)]
        fig2 = px.line(ltp_df.melt(id_vars="Strike", value_vars=["CE LTP", "PE LTP"]),
                       x="Strike", y="value", color="variable", markers=True,
                       title="Option Premiums")
        fig2.add_vline(x=spot, line_dash="dot", line_color="yellow")
        st.plotly_chart(fig2, use_container_width=True)

# =============================================================================
# MAIN APP
# =============================================================================
def main():
    symbol, sec_id, expiry, refresh = render_sidebar()

    # Fetch data
    raw_data = fetch_chain(sec_id, expiry)
    if not raw_data:
        st.error("No data received. Check API or network.")
        return

    df, spot = process_option_chain(raw_data)

    # Store previous data for delta calculations
    if st.session_state.previous_data is None:
        st.session_state.previous_data = df.copy()
    prev_df = st.session_state.previous_data

    # Add OI changes
    df = add_oi_change(df, prev_df)

    # Detect buildup types and writing/buying
    df = detect_buildup(df)
    df = detect_writing_vs_buying(df)

    # Compute OI velocity
    df = compute_oi_velocity(df, prev_df)

    # Compute PCR
    atm_strike = df.iloc[(df["Strike"] - spot).abs().argsort()[:1]]["Strike"].values[0]
    pcr_total, pcr_atm = compute_pcr(df, atm_strike)

    # Compute support/resistance
    resistance, support = compute_support_resistance(df)

    # Compute Max Pain
    max_pain = compute_max_pain(df, spot)

    # Compute Delta Exposure
    net_delta = compute_delta_exposure(df)

    # FII/DII (placeholder)
    fii_net, dii_net = add_fii_dii_placeholder()

    # Detect traps
    call_trap, put_trap = detect_traps(df, pcr_total, spot)

    # Generate signals
    df = generate_signals(df, spot, pcr_total, pcr_atm, net_delta, fii_net, dii_net)

    # Select best strikes
    best_ce, best_pe = select_best_strike(df, spot)

    # Total OI
    total_oi = compute_total_oi(df)

    # UI Tabs
    tab_overview, tab_oi, tab_sr, tab_signals, tab_strike, tab_charts = st.tabs(
        ["📊 Overview", "🔍 OI Analysis", "🛡️ S/R", "💡 Signals", "🎯 Strike Selection", "📈 Charts"]
    )

    with tab_overview:
        render_overview_tab(df, spot, pcr_total, pcr_atm, total_oi, max_pain, net_delta, fii_net, dii_net)

    with tab_oi:
        render_oi_analysis_tab(df, prev_df)

    with tab_sr:
        render_support_resistance_tab(df, support, resistance, spot)

    with tab_signals:
        render_signal_tab(df)

    with tab_strike:
        render_strike_selection_tab(df, best_ce, best_pe, spot, atm_strike)

    with tab_charts:
        render_charts_tab(df, spot, support, resistance)

    # Update session state with current data for next run
    st.session_state.previous_data = df.copy()

if __name__ == "__main__":
    main()
