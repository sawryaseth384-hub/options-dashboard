import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

from core import token_manager
from dhan_data.option_chain import get_expiry_list as fetch_expiry_list, get_option_chain as fetch_option_chain

st.set_page_config(page_title="🔥 AI Option Trading System", layout="wide")

# ---------- Helper: Fetch Expiry List ----------
def get_expiry_list(underlying_scrip=13, segment="NSE_INDEX"):
    expiries, err = fetch_expiry_list(underlying_scrip, segment)
    if err:
        return {"_error": err}
    return expiries

# ---------- Helper: Fetch Option Chain ----------
def get_option_chain(underlying_scrip=13, segment="NSE_INDEX", expiry=None):
    if expiry is None:
        expiries = get_expiry_list(underlying_scrip, segment)
        if isinstance(expiries, dict) and expiries.get("_error"):
            return expiries
        if not expiries:
            return None
        expiry = expiries[0]
    data, err = fetch_option_chain(underlying_scrip, expiry=expiry, segment=segment)
    if err:
        return {"_error": err}
    return data

# ---------- Dashboard UI ----------
st.title("🔥 AI Option Trading Dashboard")
st.markdown("### Live Data + AI Signals")


def _show_credential_status():
    client_id, token = token_manager.get_credential_status()
    st.sidebar.subheader("Credentials")
    st.sidebar.write(f"CLIENT_ID loaded: {bool(client_id)}")
    st.sidebar.write(f"DHAN_ACCESS_TOKEN loaded: {bool(token)}")
    return client_id, token


client_id, token = _show_credential_status()
if not client_id or not token:
    st.error(
        "Missing credentials. Set CLIENT_ID and DHAN_ACCESS_TOKEN in Streamlit secrets "
        "(primary) or environment variables."
    )
    st.code('CLIENT_ID = "your_client_id"\nDHAN_ACCESS_TOKEN = "your_access_token"', language="toml")
    st.info("Once updated, reload this page to fetch live data.")
    st.stop()


def render_dashboard():
    # Symbol input (dropdown)
    symbol = st.selectbox("Select Underlying", ["NIFTY", "BANKNIFTY", "FINNIFTY"])
    security_map = {"NIFTY": 13, "BANKNIFTY": 25, "FINNIFTY": 27}
    security_id = security_map[symbol]

    # Fetch expiry list
    expiries = get_expiry_list(security_id)
    if isinstance(expiries, dict) and expiries.get("_error"):
        st.error(expiries["_error"])
        st.info("Check your token and Data API subscription.")
        return
    if not expiries:
        st.error("No expiry dates found. Check your token and Data API subscription.")
        return

    selected_expiry = st.selectbox("Select Expiry", expiries)

    # Fetch option chain
    option_data = get_option_chain(security_id, expiry=selected_expiry)
    if isinstance(option_data, dict) and option_data.get("_error"):
        st.error(option_data["_error"])
        return
    if not option_data or "data" not in option_data or "oc" not in option_data["data"]:
        st.error("Option chain data not available.")
        return

    oc = option_data["data"]["oc"]
    if not oc:
        st.error("Option chain data is empty.")
        return

    spot = option_data["data"].get("last_price", 0)

    # Convert to DataFrame for analysis
    rows = []
    for strike_str, opts in oc.items():
        strike = float(strike_str)
        ce = opts.get("ce", {})
        pe = opts.get("pe", {})
        rows.append({
            "Strike": strike,
            "Call OI": ce.get("oi", 0),
            "Call LTP": ce.get("last_price", 0),
            "Call IV": ce.get("implied_volatility", 0),
            "Call Delta": ce.get("greeks", {}).get("delta", 0),
            "Put OI": pe.get("oi", 0),
            "Put LTP": pe.get("last_price", 0),
            "Put IV": pe.get("implied_volatility", 0),
            "Put Delta": pe.get("greeks", {}).get("delta", 0),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        st.error("Option chain data not available.")
        return

    df = df.sort_values("Strike")

    # ---- Analytics ----
    total_call_oi = df["Call OI"].sum()
    total_put_oi = df["Put OI"].sum()
    pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0

    atm_strike = df.iloc[(df["Strike"] - spot).abs().argsort()[:1]]["Strike"].values[0]
    atm_row = df[df["Strike"] == atm_strike].iloc[0]

    call_strength = atm_row["Call OI"] / total_call_oi * 100 if total_call_oi > 0 else 0
    put_strength = atm_row["Put OI"] / total_put_oi * 100 if total_put_oi > 0 else 0

    if pcr > 1.2:
        signal = "📉 BEARISH (High Put OI)"
    elif pcr < 0.8:
        signal = "📈 BULLISH (High Call OI)"
    else:
        if call_strength > put_strength:
            signal = "⚖️ NEUTRAL with Call Bias"
        else:
            signal = "⚖️ NEUTRAL with Put Bias"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Spot Price", f"{spot:,.2f}")
    col2.metric("Put‑Call Ratio (PCR)", f"{pcr:.2f}")
    col3.metric("ATM Strike", f"{atm_strike:.0f}")
    col4.metric("AI Signal", signal)

    st.subheader("📊 Top OI Strikes")
    top_oi = df.nlargest(5, "Call OI")[["Strike", "Call OI", "Put OI"]]
    st.dataframe(top_oi, use_container_width=True)

    st.subheader("📋 Full Option Chain")
    st.dataframe(df.style.format({
        "Call OI": "{:,.0f}", "Put OI": "{:,.0f}",
        "Call LTP": "{:.2f}", "Put LTP": "{:.2f}",
        "Call IV": "{:.2f}%", "Put IV": "{:.2f}%",
        "Call Delta": "{:.3f}", "Put Delta": "{:.3f}"
    }), use_container_width=True)

    st.subheader("📈 OI Distribution (ATM ± 5 strikes)")
    atm_index = df[df["Strike"] == atm_strike].index[0]
    start = max(0, atm_index - 5)
    end = min(len(df), atm_index + 6)
    oi_subset = df.iloc[start:end][["Strike", "Call OI", "Put OI"]].set_index("Strike")
    st.bar_chart(oi_subset)

    st.caption("Data refreshes on page reload. Update DHAN_ACCESS_TOKEN if it expires.")


render_dashboard()
