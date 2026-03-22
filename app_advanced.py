import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="🔥 AI Option Trading System", layout="wide")

# ---------- Authentication ----------
ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]
CLIENT_ID = st.secrets["CLIENT_ID"]
headers = {
    "access-token": ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json"
}

# ---------- Helper: Fetch Expiry List ----------
def get_expiry_list(underlying_scrip=13, segment="IDX_I"):
    url = "https://api.dhan.co/v2/optionchain/expirylist"
    payload = {"UnderlyingScrip": underlying_scrip, "UnderlyingSeg": segment}
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("status") == "success":
            return data.get("data", [])
    return []

# ---------- Helper: Fetch Option Chain ----------
def get_option_chain(underlying_scrip=13, segment="IDX_I", expiry=None):
    if expiry is None:
        expiries = get_expiry_list(underlying_scrip, segment)
        if not expiries:
            return None
        expiry = expiries[0]
    url = "https://api.dhan.co/v2/optionchain"
    payload = {"UnderlyingScrip": underlying_scrip, "UnderlyingSeg": segment, "Expiry": expiry}
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("status") == "success":
            return data
    return None

# ---------- Dashboard UI ----------
st.title("🔥 AI Option Trading Dashboard")
st.markdown("### Live Data + AI Signals")

# Symbol input (dropdown)
symbol = st.selectbox("Select Underlying", ["NIFTY", "BANKNIFTY", "FINNIFTY"])
security_map = {"NIFTY": 13, "BANKNIFTY": 25, "FINNIFTY": 27}
security_id = security_map[symbol]

# Fetch expiry list
expiries = get_expiry_list(security_id)
if not expiries:
    st.error("No expiry dates found. Check your token and Data API subscription.")
    st.stop()

selected_expiry = st.selectbox("Select Expiry", expiries)

# Fetch option chain
option_data = get_option_chain(security_id, expiry=selected_expiry)
if not option_data or "data" not in option_data or "oc" not in option_data["data"]:
    st.error("Option chain data not available.")
    st.stop()

oc = option_data["data"]["oc"]
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
df = pd.DataFrame(rows).sort_values("Strike")

# ---- Analytics ----
# Put‑Call Ratio (PCR)
total_call_oi = df["Call OI"].sum()
total_put_oi = df["Put OI"].sum()
pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0

# OI concentration – find ATM strike
atm_strike = df.iloc[(df["Strike"] - spot).abs().argsort()[:1]]["Strike"].values[0]
atm_row = df[df["Strike"] == atm_strike].iloc[0]

# Strength: OI change (if we had previous data, we could compute change; for now use current OI)
call_strength = atm_row["Call OI"] / total_call_oi * 100 if total_call_oi > 0 else 0
put_strength = atm_row["Put OI"] / total_put_oi * 100 if total_put_oi > 0 else 0

# Simple AI signal based on PCR and ATM OI
if pcr > 1.2:
    signal = "📉 BEARISH (High Put OI)"
    color = "red"
elif pcr < 0.8:
    signal = "📈 BULLISH (High Call OI)"
    color = "green"
else:
    if call_strength > put_strength:
        signal = "⚖️ NEUTRAL with Call Bias"
        color = "orange"
    else:
        signal = "⚖️ NEUTRAL with Put Bias"
        color = "orange"

# ---- Display ----
col1, col2, col3, col4 = st.columns(4)
col1.metric("Spot Price", f"{spot:,.2f}")
col2.metric("Put‑Call Ratio (PCR)", f"{pcr:.2f}")
col3.metric("ATM Strike", f"{atm_strike:.0f}")
col4.metric("AI Signal", signal)

# Show top OI strikes
st.subheader("📊 Top OI Strikes")
top_oi = df.nlargest(5, "Call OI")[["Strike", "Call OI", "Put OI"]]
st.dataframe(top_oi, use_container_width=True)

# Full option chain
st.subheader("📋 Full Option Chain")
st.dataframe(df.style.format({
    "Call OI": "{:,.0f}", "Put OI": "{:,.0f}",
    "Call LTP": "{:.2f}", "Put LTP": "{:.2f}",
    "Call IV": "{:.2f}%", "Put IV": "{:.2f}%",
    "Call Delta": "{:.3f}", "Put Delta": "{:.3f}"
}), use_container_width=True)

# Optional: Plot OI distribution (simple bar)
st.subheader("📈 OI Distribution (ATM ± 5 strikes)")
atm_index = df[df["Strike"] == atm_strike].index[0]
start = max(0, atm_index - 5)
end = min(len(df), atm_index + 6)
oi_subset = df.iloc[start:end][["Strike", "Call OI", "Put OI"]].set_index("Strike")
st.bar_chart(oi_subset)

st.caption("Data refreshes on page reload. Token expires in 24h – renew as needed.")
