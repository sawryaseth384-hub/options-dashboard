import sys
import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import threading
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain
from dhan_data.live_market_feed import start_live_feed, subscribe_instrument, get_live_ltp
from dhan_data.depth_feed import start_depth_feed, subscribe_depth, get_depth
from dhan_data.chart import get_candle_data, plot_candle
from dhan_data.historical_data import get_historical
from dhan_data.instruments import get_symbol_data

# =============================================================================
# CONFIG
# =============================================================================
st.set_page_config(page_title="🧠 Pro Options Dashboard", layout="wide")
st.title("🧠 Smart Money Options Dashboard — Institutional Grade")

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
if "previous_data" not in st.session_state:
    st.session_state.previous_data = None
if "live_ltp" not in st.session_state:
    st.session_state.live_ltp = 0
if "depth_data" not in st.session_state:
    st.session_state.depth_data = {"bids": [], "asks": []}
if "ws_started" not in st.session_state:
    st.session_state.ws_started = False
if "symbol" not in st.session_state:
    st.session_state.symbol = "NIFTY"
if "sec_id" not in st.session_state:
    st.session_state.sec_id = None
if "segment" not in st.session_state:
    st.session_state.segment = None
if "expiry" not in st.session_state:
    st.session_state.expiry = None
if "error" not in st.session_state:
    st.session_state.error = None

# =============================================================================
# WEBSOCKET HELPERS
# =============================================================================
def start_websockets():
    if not st.session_state.ws_started:
        try:
            start_live_feed()
            start_depth_feed()
            st.session_state.ws_started = True
        except Exception as e:
            st.session_state.error = f"WebSocket start error: {e}"

def subscribe_to_symbol(symbol):
    sec_id, segment = get_symbol_data(symbol)
    if sec_id:
        st.session_state.sec_id = sec_id
        st.session_state.segment = segment
        try:
            subscribe_instrument(sec_id, segment)
            subscribe_depth(sec_id, segment)
        except Exception as e:
            st.session_state.error = f"Subscribe error: {e}"
    else:
        st.session_state.error = f"Symbol {symbol} not found"

# =============================================================================
# DATA FETCHING (cached)
# =============================================================================
@st.cache_data(ttl=3600)
def fetch_expiry(sec_id):
    if sec_id is None:
        return []
    data = get_expiry(sec_id)
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "data" in data:
        return data["data"]
    return []

@st.cache_data(ttl=300)
def fetch_chain(sec_id, exp):
    if sec_id is None or not exp:
        return {}
    data = get_option_chain(sec_id, exp)
    if not data or "data" not in data:
        if data.get("error"):
            st.session_state.error = f"Option chain error: {data['error']}"
        return {}
    inner = data["data"]
    if isinstance(inner, dict) and "data" in inner:
        inner = inner["data"]
    return inner

# =============================================================================
# DATA PROCESSING FUNCTIONS
# =============================================================================
def process_option_chain(raw_data):
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
            "PE OI": pe.get("oi", 0),
            "PE LTP": pe.get("last_price", 0),
            "PE Delta": pe.get("greeks", {}).get("delta", 0),
            "PE Gamma": pe.get("greeks", {}).get("gamma", 0),
            "PE Theta": pe.get("greeks", {}).get("theta", 0),
            "PE Vega": pe.get("greeks", {}).get("vega", 0),
        })
    df = pd.DataFrame(rows).sort_values("Strike")
    return df, spot

def add_oi_change(df, prev_df):
    if prev_df is not None:
        merged = df.merge(prev_df, on="Strike", suffixes=("", "_prev"))
        df["CE OI Change"] = merged["CE OI"] - merged["CE OI_prev"]
        df["PE OI Change"] = merged["PE OI"] - merged["PE OI_prev"]
        df["CE Price Change"] = merged["CE LTP"] - merged["CE LTP_prev"]
        df["PE Price Change"] = merged["PE LTP"] - merged["PE LTP_prev"]
    else:
        df["CE OI Change"] = 0
        df["PE OI Change"] = 0
        df["CE Price Change"] = 0
        df["PE Price Change"] = 0
    return df

def detect_buildup(df):
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
    def classify(row):
        if row["CE OI Change"] > 0 and row["CE Price Change"] < 0:
            ce_action = "Writing"
        elif row["CE OI Change"] > 0 and row["CE Price Change"] > 0:
            ce_action = "Buying"
        else:
            ce_action = "Neutral"
        if row["PE OI Change"] > 0 and row["PE Price Change"] < 0:
            pe_action = "Writing"
        elif row["PE OI Change"] > 0 and row["PE Price Change"] > 0:
            pe_action = "Buying"
        else:
            pe_action = "Neutral"
        return ce_action, pe_action

    df[["CE Action", "PE Action"]] = df.apply(
        lambda row: pd.Series(classify(row)), axis=1
    )
    return df

def compute_oi_velocity(df, prev_df):
    if prev_df is not None:
        df["CE OI Velocity"] = df["CE OI"] - prev_df["CE OI"]
        df["PE OI Velocity"] = df["PE OI"] - prev_df["PE OI"]
    else:
        df["CE OI Velocity"] = 0
        df["PE OI Velocity"] = 0
    return df

def compute_oi_divergence(df):
    # Simple divergence: sign of OI change vs price change
    df["CE OI Divergence"] = np.sign(df["CE OI Change"]) * np.sign(df["CE Price Change"])
    df["PE OI Divergence"] = np.sign(df["PE OI Change"]) * np.sign(df["PE Price Change"])
    df["CE OI Divergence"] = df["CE OI Divergence"].apply(
        lambda x: "Bullish" if x == 1 else ("Bearish" if x == -1 else "Neutral")
    )
    df["PE OI Divergence"] = df["PE OI Divergence"].apply(
        lambda x: "Bullish" if x == 1 else ("Bearish" if x == -1 else "Neutral")
    )
    return df

def compute_oi_shift(df, prev_df):
    if prev_df is not None:
        max_ce_prev = prev_df.loc[prev_df["CE OI"].idxmax(), "Strike"]
        max_ce_curr = df.loc[df["CE OI"].idxmax(), "Strike"]
        max_pe_prev = prev_df.loc[prev_df["PE OI"].idxmax(), "Strike"]
        max_pe_curr = df.loc[df["PE OI"].idxmax(), "Strike"]
        ce_shift = max_ce_curr - max_ce_prev
        pe_shift = max_pe_curr - max_pe_prev
    else:
        ce_shift = 0
        pe_shift = 0
    df["CE OI Shift"] = ce_shift
    df["PE OI Shift"] = pe_shift
    return df

def compute_pcr(df, atm_strike=None):
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
    resistance = df.nlargest(top_n, "CE OI")["Strike"].tolist()
    support = df.nlargest(top_n, "PE OI")["Strike"].tolist()
    return resistance, support

def compute_max_pain(df, spot):
    strikes = df["Strike"].values
    pain_values = []
    for strike in strikes:
        ce_pain = ((df["Strike"] - strike).clip(lower=0) * df["CE OI"]).sum()
        pe_pain = ((strike - df["Strike"]).clip(lower=0) * df["PE OI"]).sum()
        pain_values.append((strike, ce_pain + pe_pain))
    max_pain_strike = min(pain_values, key=lambda x: x[1])[0]
    return max_pain_strike

def compute_delta_exposure(df):
    df["CE Delta Exposure"] = df["CE Delta"] * df["CE OI"]
    df["PE Delta Exposure"] = -df["PE Delta"] * df["PE OI"]
    net_delta = df["CE Delta Exposure"].sum() + df["PE Delta Exposure"].sum()
    return net_delta

def detect_traps(df, pcr_total, spot):
    max_ce_strike = df.loc[df["CE OI"].idxmax(), "Strike"]
    max_pe_strike = df.loc[df["PE OI"].idxmax(), "Strike"]
    call_trap = (spot > max_ce_strike) and (pcr_total < 0.7)
    put_trap = (spot < max_pe_strike) and (pcr_total > 1.3)
    return call_trap, put_trap

def generate_signals(df, spot, pcr_total, pcr_atm, net_delta):
    df["Signal"] = "Neutral"
    df["Signal Reason"] = ""
    for idx, row in df.iterrows():
        if pcr_total > 1 and row["CE Delta"] > 0.5:
            df.at[idx, "Signal"] = "BUY CE"
            df.at[idx, "Signal Reason"] = "PCR >1 + high CE delta"
        elif pcr_total < 0.7 and row["PE Delta"] < -0.5:
            df.at[idx, "Signal"] = "BUY PE"
            df.at[idx, "Signal Reason"] = "PCR <0.7 + high PE delta"
        if row["CE BuildUp"] == "CE Long Build-up" and pcr_total > 1:
            df.at[idx, "Signal"] = "STRONG BUY CE"
            df.at[idx, "Signal Reason"] = "Long build-up + bullish PCR"
        elif row["PE BuildUp"] == "PE Long Build-up" and pcr_total < 0.7:
            df.at[idx, "Signal"] = "STRONG BUY PE"
            df.at[idx, "Signal Reason"] = "Long build-up + bearish PCR"
    return df

def select_best_strike(df, spot):
    df["CE Delta Diff"] = abs(df["CE Delta"] - 0.5)
    best_ce = df.nsmallest(1, "CE Delta Diff").iloc[0]["Strike"]
    df["PE Delta Diff"] = abs(df["PE Delta"] + 0.5)
    best_pe = df.nsmallest(1, "PE Delta Diff").iloc[0]["Strike"]
    return best_ce, best_pe

def get_oi_history(sec_id, strike, segment):
    # Placeholder – you can replace with actual historical OI fetch
    return [1000, 1200, 1400, 1600, 1800]

# =============================================================================
# SIDEBAR (no st.stop())
# =============================================================================
with st.sidebar:
    st.header("⚙️ Controls")
    symbol = st.text_input("Symbol", value=st.session_state.symbol)
    if symbol != st.session_state.symbol:
        st.session_state.symbol = symbol
        sec_id, segment = get_symbol_data(symbol)
        st.session_state.sec_id = sec_id
        st.session_state.segment = segment
        if st.session_state.sec_id:
            st.success(f"✅ Symbol ID: {st.session_state.sec_id}")
        else:
            st.error(f"❌ Symbol '{symbol}' not found. Please enter a valid symbol (e.g., NIFTY, BANKNIFTY).")

    # Get expiry list only if sec_id is valid
    if st.session_state.sec_id:
        expiry_list = fetch_expiry(st.session_state.sec_id)
        if expiry_list:
            expiry = st.selectbox("Expiry", expiry_list, index=0 if st.session_state.expiry is None else expiry_list.index(st.session_state.expiry) if st.session_state.expiry in expiry_list else 0)
            st.session_state.expiry = expiry
        else:
            st.warning("No expiry data. Check your connection or token.")
    else:
        st.info("Enter a valid symbol to load expiry dates.")

    refresh = st.button("🔄 Refresh Data")
    if refresh:
        st.cache_data.clear()
        st.rerun()

    # Depth display (optional)
    st.divider()
    st.subheader("📊 Depth (Bid/Ask)")
    depth = get_depth()
    if depth["bids"]:
        st.write("**Bids**")
        st.dataframe(pd.DataFrame(depth["bids"][:5]), use_container_width=True)
    if depth["asks"]:
        st.write("**Asks**")
        st.dataframe(pd.DataFrame(depth["asks"][:5]), use_container_width=True)

# =============================================================================
# MAIN APP – only if we have valid data
# =============================================================================
if st.session_state.sec_id and st.session_state.expiry:
    # Start websockets
    start_websockets()
    subscribe_to_symbol(st.session_state.symbol)

    # Fetch option chain
    raw_data = fetch_chain(st.session_state.sec_id, st.session_state.expiry)
    if not raw_data:
        st.error("No data received from API. Check your connection or token.")
    else:
        # Process data
        df, spot = process_option_chain(raw_data)
        prev_df = st.session_state.previous_data

        # Add derived columns
        df = add_oi_change(df, prev_df)
        df = detect_buildup(df)
        df = detect_writing_vs_buying(df)
        df = compute_oi_velocity(df, prev_df)
        df = compute_oi_divergence(df)
        df = compute_oi_shift(df, prev_df)

        # Key indicators
        atm_strike = df.iloc[(df["Strike"] - spot).abs().argsort()[:1]]["Strike"].values[0]
        pcr_total, pcr_atm = compute_pcr(df, atm_strike)
        resistance, support = compute_support_resistance(df)
        max_pain = compute_max_pain(df, spot)
        net_delta = compute_delta_exposure(df)
        call_trap, put_trap = detect_traps(df, pcr_total, spot)
        best_ce, best_pe = select_best_strike(df, spot)
        df = generate_signals(df, spot, pcr_total, pcr_atm, net_delta)

        # Save for next run
        st.session_state.previous_data = df.copy()

        # ========== LAYERED UI ==========
        # Level 1 – Decision Bar
        st.markdown("---")
        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
        col1.metric("📍 Spot Price", f"{st.session_state.live_ltp:.2f}" if st.session_state.live_ltp else f"{spot:.2f}")
        col2.metric("📊 PCR", f"{pcr_total:.2f}")
        col3.metric("🧠 Market Bias", "🟢 Bullish" if pcr_total > 1 else ("🔴 Bearish" if pcr_total < 0.7 else "⚪ Neutral"))
        col4.metric("🎯 ATM Strike", f"{atm_strike}")
        col5.metric("🔥 Best Strike", f"{best_ce} CE")
        col6.metric("🚀 Final Signal", df[df["Signal"] != "Neutral"]["Signal"].iloc[0] if not df[df["Signal"] != "Neutral"].empty else "Neutral")
        col7.metric("⚠️ Trap Alert", "Call Trap" if call_trap else ("Put Trap" if put_trap else "No Trap"))
        st.markdown("---")

        # Level 2 – Core Analysis
        with st.container():
            st.subheader("📌 Core Analysis")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.success(f"🟢 Support: {support[0] if support else 'N/A'}")
            c2.error(f"🔴 Resistance: {resistance[0] if resistance else 'N/A'}")
            c3.info(f"🎯 Max Pain: {max_pain}")
            c4.info(f"📊 ATM PCR: {pcr_atm:.2f}" if not np.isnan(pcr_atm) else "ATM PCR: N/A")
            c5.info(f"🔥 OI Strength: {'High' if pcr_total > 1.2 or pcr_total < 0.8 else 'Moderate'}")

        # Level 3 – Option Chain Table
        st.subheader("📋 Option Chain + Advanced OI")
        display_cols = [
            "Strike", "CE OI", "PE OI", "CE OI Change", "PE OI Change",
            "CE LTP", "PE LTP", "CE Delta", "PE Delta",
            "CE BuildUp", "PE BuildUp", "Signal",
            "CE OI Velocity", "PE OI Velocity",
            "CE OI Divergence", "PE OI Divergence",
            "CE OI Shift", "PE OI Shift",
            "CE Action", "PE Action"
        ]
        available_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available_cols].style.format({
            "CE OI": "{:,.0f}",
            "PE OI": "{:,.0f}",
            "CE OI Change": "{:,.0f}",
            "PE OI Change": "{:,.0f}",
            "CE LTP": "{:.2f}",
            "PE LTP": "{:.2f}",
            "CE Delta": "{:.3f}",
            "PE Delta": "{:.3f}",
            "CE OI Velocity": "{:,.0f}",
            "PE OI Velocity": "{:,.0f}",
        }), use_container_width=True, height=500)

        # Level 4 – Charts
        st.subheader("📈 Charts")
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            fig_oi = px.bar(df, x="Strike", y=["CE OI", "PE OI"], barmode="group", title="Open Interest by Strike")
            for s in support[:2]:
                fig_oi.add_vline(x=s, line_dash="dash", line_color="green", annotation_text="Support")
            for r in resistance[:2]:
                fig_oi.add_vline(x=r, line_dash="dash", line_color="red", annotation_text="Resistance")
            fig_oi.add_vline(x=spot, line_dash="dot", line_color="yellow", annotation_text="Spot")
            st.plotly_chart(fig_oi, use_container_width=True)
        with chart_col2:
            ltp_df = df.melt(id_vars="Strike", value_vars=["CE LTP", "PE LTP"], var_name="Option", value_name="LTP")
            fig_ltp = px.line(ltp_df, x="Strike", y="LTP", color="Option", title="Option Premiums", markers=True)
            fig_ltp.add_vline(x=spot, line_dash="dot", line_color="yellow")
            st.plotly_chart(fig_ltp, use_container_width=True)

        # Candlestick Chart (if available)
        if st.session_state.sec_id:
            try:
                df_candle = get_candle_data(st.session_state.sec_id, st.session_state.segment)
                if df_candle is not None:
                    fig_candle, trend = plot_candle(df_candle)
                    st.subheader(f"🕯️ Candlestick (Spot) — Trend: {trend}")
                    st.plotly_chart(fig_candle, use_container_width=True)
            except Exception as e:
                st.warning(f"Candlestick error: {e}")

        # Level 5 – Strike Analysis
        st.subheader("🔍 Strike Analysis")
        selected_strike = st.selectbox("Select Strike", df["Strike"].tolist())
        if selected_strike:
            row = df[df["Strike"] == selected_strike].iloc[0]
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**CE OI**: {row['CE OI']:,.0f}")
                st.write(f"**CE LTP**: {row['CE LTP']:.2f}")
                st.write(f"**CE Delta**: {row['CE Delta']:.3f}")
                st.write(f"**CE BuildUp**: {row['CE BuildUp']}")
                st.write(f"**CE Action**: {row['CE Action']}")
            with col_b:
                st.write(f"**PE OI**: {row['PE OI']:,.0f}")
                st.write(f"**PE LTP**: {row['PE LTP']:.2f}")
                st.write(f"**PE Delta**: {row['PE Delta']:.3f}")
                st.write(f"**PE BuildUp**: {row['PE BuildUp']}")
                st.write(f"**PE Action**: {row['PE Action']}")

            st.write("**OI Velocity Graph** (last 5 intervals)")
            history_ce = get_oi_history(st.session_state.sec_id, selected_strike, "CE")
            history_pe = get_oi_history(st.session_state.sec_id, selected_strike, "PE")
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Scatter(y=history_ce, name="CE OI", mode="lines+markers"))
            fig_hist.add_trace(go.Scatter(y=history_pe, name="PE OI", mode="lines+markers"))
            fig_hist.update_layout(title="OI History (Mock)", height=300)
            st.plotly_chart(fig_hist, use_container_width=True)

        # Level 6 – Pro Insights
        st.subheader("🚀 Pro Insights")
        pro1, pro2, pro3, pro4 = st.columns(4)
        pro1.metric("FII Net Position (cr)", "1,240")  # Placeholder
        pro2.metric("DII Net Position (cr)", "-320")   # Placeholder
        pro3.metric("IV (ATM)", "14.8%")              # Placeholder
        pro4.metric("Gamma Exposure", "₹4.2 Lakh / pt") # Placeholder
        st.write(f"**Delta Exposure:** {net_delta:,.0f}")

        # Optional auto-refresh (uncomment after everything works)
        # time.sleep(5)
        # st.rerun()

else:
    st.info("Please select a valid symbol and expiry to see the dashboard.")
