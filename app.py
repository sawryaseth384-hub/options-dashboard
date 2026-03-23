import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from core.token_manager import get_headers
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain

st.set_page_config(page_title="Dhan Options Dashboard", layout="wide")

st.title("📊 Dhan Options Dashboard")

# =========================
# Symbol
# =========================
symbol = st.text_input("Symbol", "NIFTY")
SECURITY_ID = 13

st.write(f"🔍 {symbol} security ID:", SECURITY_ID)

# =========================
# Expiry
# =========================
expiry_list = []

try:
    expiry_data = get_expiry(SECURITY_ID)
    st.write("📦 Expiry Raw:", expiry_data)

    if isinstance(expiry_data, list):
        expiry_list = expiry_data
    elif isinstance(expiry_data, dict) and "data" in expiry_data:
        expiry_list = expiry_data["data"]

except Exception as e:
    st.error(f"❌ Expiry Error: {e}")

if not expiry_list:
    st.warning("⚠️ No expiry found")
    st.stop()

expiry = st.selectbox("Select Expiry", expiry_list)

# =========================
# Option Chain
# =========================
import pandas as pd

st.subheader("📊 Option Chain (OI + Greeks)")

option_data = get_option_chain(SECURITY_ID, expiry)

# DEBUG
st.write("RAW:", option_data)

# =========================
# SAFE EXTRACTION
# =========================
try:
    oc = option_data["data"]["data"]["oc"]
except:
    st.error("❌ OC data not found")
    st.stop()

rows = []

for strike, values in oc.items():

    ce = values.get("ce", {})
    pe = values.get("pe", {})

    ce_greeks = ce.get("greeks", {})
    pe_greeks = pe.get("greeks", {})

    rows.append({
        # CE
        "CE OI": ce.get("oi", 0),
        "CE LTP": ce.get("last_price", 0),
        "CE Delta": ce_greeks.get("delta", 0),
        "CE Theta": ce_greeks.get("theta", 0),
        "CE IV": ce.get("implied_volatility", 0),

        # Strike
        "Strike": float(strike),

        # PE
        "PE IV": pe.get("implied_volatility", 0),
        "PE Theta": pe_greeks.get("theta", 0),
        "PE Delta": pe_greeks.get("delta", 0),
        "PE LTP": pe.get("last_price", 0),
        "PE OI": pe.get("oi", 0),
    })

df = pd.DataFrame(rows).sort_values("Strike")

# 🔥 Highlight max OI
df["CE Signal"] = df["CE OI"].apply(lambda x: "🔥" if x == df["CE OI"].max() else "")
df["PE Signal"] = df["PE OI"].apply(lambda x: "🔥" if x == df["PE OI"].max() else "")

st.dataframe(df, use_container_width=True)
