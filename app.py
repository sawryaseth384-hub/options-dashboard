import sys, os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dhan_data.instruments import get_symbol_data
from dhan_data.option_chain import get_option_chain
from dhan_data.expiry import get_expiry
from core.token_manager import get_headers

st.set_page_config(layout="wide")
st.title("🧠 Smart Money Options Dashboard — Institutional Grade")

# Session state
if "previous_data" not in st.session_state:
    st.session_state.previous_data = None
if "sec_id" not in st.session_state:
    st.session_state.sec_id = None
if "segment" not in st.session_state:
    st.session_state.segment = None
if "expiry" not in st.session_state:
    st.session_state.expiry = None
if "symbol" not in st.session_state:
    st.session_state.symbol = "NIFTY"

# ------------------- SIDEBAR -------------------
with st.sidebar:
    st.header("⚙️ Controls")
    symbol = st.text_input("Symbol", st.session_state.symbol).upper()
    if symbol != st.session_state.symbol:
        st.session_state.symbol = symbol
        sec_id, seg = get_symbol_data(symbol)
        st.session_state.sec_id = sec_id
        st.session_state.segment = seg
        if sec_id:
            st.success(f"✅ {symbol} → ID: {sec_id}, Segment: {seg}")
        else:
            st.error(f"❌ Symbol '{symbol}' not found. Try NIFTY, BANKNIFTY, or a stock like RELIANCE.")

    if st.session_state.sec_id:
        # Expiry list fetch
        expiry_list = []
        try:
            expiry_data = get_expiry(st.session_state.sec_id)
            if isinstance(expiry_data, list):
                expiry_list = expiry_data
            elif isinstance(expiry_data, dict) and "data" in expiry_data:
                expiry_list = expiry_data["data"]
        except Exception as e:
            st.warning(f"Expiry fetch error: {e}")

        if expiry_list:
            expiry = st.selectbox("Expiry", expiry_list, index=0 if st.session_state.expiry is None else expiry_list.index(st.session_state.expiry) if st.session_state.expiry in expiry_list else 0)
            st.session_state.expiry = expiry
        else:
            # Fallback: generate next Thursday
            fallback_expiry = (datetime.now() + timedelta(days=(3 - datetime.now().weekday() + 7) % 7)).strftime("%Y-%m-%d")
            st.warning(f"No expiry from API. Using fallback: {fallback_expiry}")
            st.session_state.expiry = fallback_expiry

    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

# ------------------- MAIN APP -------------------
if st.session_state.sec_id and st.session_state.expiry:
    # Fetch option chain
    @st.cache_data(ttl=60)
    def fetch_chain(sec_id, expiry, segment):
        return get_option_chain(sec_id, expiry, segment)

    data = fetch_chain(st.session_state.sec_id, st.session_state.expiry, st.session_state.segment)
    if not data or "data" not in data:
        st.error("No option chain data. Check symbol/expiry.")
        st.stop()

    # Process data (same functions as before)
    def process_option_chain(raw):
        spot = raw.get("last_price", 0)
        oc = raw.get("oc", {})
        rows = []
        for strike, val in oc.items():
            ce = val.get("ce", {})
            pe = val.get("pe", {})
            rows.append({
                "Strike": int(float(strike)),
                "CE OI": ce.get("oi", 0),
                "CE LTP": ce.get("last_price", 0),
                "CE Delta": ce.get("greeks", {}).get("delta", 0),
                "PE OI": pe.get("oi", 0),
                "PE LTP": pe.get("last_price", 0),
                "PE Delta": pe.get("greeks", {}).get("delta", 0),
            })
        df = pd.DataFrame(rows).sort_values("Strike")
        return df, spot

    df, spot = process_option_chain(data["data"])

    # Compute basic indicators
    atm_idx = (df["Strike"] - spot).abs().argsort()[0]
    atm_strike = df.iloc[atm_idx]["Strike"]

    total_ce = df["CE OI"].sum()
    total_pe = df["PE OI"].sum()
    pcr = total_pe / total_ce if total_ce else 0

    support = df.nlargest(3, "PE OI")["Strike"].tolist()
    resistance = df.nlargest(3, "CE OI")["Strike"].tolist()

    # ------------------- LAYERED UI -------------------
    # Level 1 – Decision Bar
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("📍 Spot", f"{spot:.2f}")
    col2.metric("📊 PCR", f"{pcr:.2f}")
    col3.metric("🧠 Bias", "Bullish" if pcr > 1 else ("Bearish" if pcr < 0.7 else "Neutral"))
    col4.metric("🎯 ATM", f"{atm_strike}")
    col5.metric("🔥 Best", f"{df.loc[df['CE Delta'].sub(0.5).abs().idxmin(), 'Strike']} CE")
    col6.metric("⚠️ Trap", "Call Trap" if (spot > resistance[0] and pcr < 0.7) else ("Put Trap" if (spot < support[0] and pcr > 1.3) else "No"))

    # Level 2 – Core Analysis
    st.subheader("📌 Core Analysis")
    c1, c2, c3 = st.columns(3)
    c1.success(f"🟢 Support: {support[0] if support else 'N/A'}")
    c2.error(f"🔴 Resistance: {resistance[0] if resistance else 'N/A'}")
    c3.info(f"🎯 Max Pain: {df.loc[df['CE OI'].sub(df['PE OI']).abs().idxmin(), 'Strike']}")

    # Level 3 – Option Chain Table
    st.subheader("📋 Option Chain")
    display_cols = ["Strike", "CE OI", "CE LTP", "CE Delta", "PE OI", "PE LTP", "PE Delta"]
    st.dataframe(df[display_cols].style.format({
        "CE OI": "{:,.0f}", "PE OI": "{:,.0f}",
        "CE LTP": "{:.2f}", "PE LTP": "{:.2f}",
        "CE Delta": "{:.3f}", "PE Delta": "{:.3f}"
    }), height=400, use_container_width=True)

    # Level 4 – Charts
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(df, x="Strike", y=["CE OI", "PE OI"], barmode="group", title="OI by Strike")
        fig.add_vline(x=spot, line_dash="dot", line_color="yellow")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.line(df, x="Strike", y=["CE LTP", "PE LTP"], title="Premiums")
        fig2.add_vline(x=spot, line_dash="dot", line_color="yellow")
        st.plotly_chart(fig2, use_container_width=True)

else:
    st.info("Select a valid symbol from sidebar to load data.")
