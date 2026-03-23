import sys
import os
import streamlit as st
import pandas as pd
import plotly.express as px

# ✅ IMPORT FIX (Streamlit Cloud)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain

st.set_page_config(page_title="Dhan Options Dashboard", layout="wide")

st.title("📊 Dhan Options Dashboard")

# =========================
# SYMBOL
# =========================
symbol = st.text_input("Symbol", "NIFTY")
SECURITY_ID = 13

st.write(f"🔍 {symbol} security ID:", SECURITY_ID)

# =========================
# EXPIRY FETCH
# =========================
expiry_list = []

try:
    expiry_data = get_expiry(SECURITY_ID)

    st.write("📦 Expiry Raw:", expiry_data)

    # ✅ HANDLE BOTH CASES
    if isinstance(expiry_data, list):
        expiry_list = expiry_data

    elif isinstance(expiry_data, dict) and "data" in expiry_data:
        expiry_list = expiry_data["data"]

except Exception as e:
    st.error(f"Expiry Error: {e}")

if not expiry_list:
    st.warning("No expiry data found")
    st.stop()

expiry = st.selectbox("Select Expiry", expiry_list)

# =========================
# OPTION CHAIN FETCH
# =========================
st.subheader("📊 Option Chain (OI + Greeks)")

option_data = get_option_chain(SECURITY_ID, expiry)

# =========================
# SAFE DATA EXTRACTION
# =========================
if not option_data:
    st.error("❌ No API response")
    st.stop()

if "error" in option_data:
    st.error(option_data["error"])
    st.stop()

if "data" not in option_data:
    st.error("❌ Invalid API format")
    st.write(option_data)
    st.stop()

# 🔥 HANDLE NESTED DATA
data_layer = option_data["data"]

if isinstance(data_layer, dict) and "data" in data_layer:
    data = data_layer["data"]
else:
    data = data_layer

# =========================
# SPOT + OC
# =========================
spot = data.get("last_price", 0)
st.success(f"📍 Spot Price: {spot}")

oc = data.get("oc", {})

if not oc:
    st.error("❌ No option chain data")
    st.write(data)
    st.stop()

# =========================
# BUILD DATAFRAME
# =========================
rows = []

for strike, val in oc.items():
    ce = val.get("ce", {})
    pe = val.get("pe", {})

    rows.append({
        "Strike": float(strike),

        "CE OI": ce.get("oi", 0),
        "CE LTP": ce.get("last_price", 0),
        "CE Delta": ce.get("greeks", {}).get("delta", 0),
        "CE Theta": ce.get("greeks", {}).get("theta", 0),

        "PE LTP": pe.get("last_price", 0),
        "PE OI": pe.get("oi", 0),
        "PE Delta": pe.get("greeks", {}).get("delta", 0),
        "PE Theta": pe.get("greeks", {}).get("theta", 0),
    })

df = pd.DataFrame(rows)

if df.empty:
    st.error("❌ DataFrame empty")
    st.stop()

df = df.sort_values("Strike")

# =========================
# ATM MARK
# =========================
df["ATM"] = df["Strike"].apply(lambda x: "⭐" if abs(x - spot) < 50 else "")

# =========================
# CE / PE STRENGTH
# =========================
df["CE 🔥"] = df["CE OI"] > df["PE OI"]
df["PE 🔥"] = df["PE OI"] > df["CE OI"]

df["CE 🔥"] = df["CE 🔥"].apply(lambda x: "🔥" if x else "")
df["PE 🔥"] = df["PE 🔥"].apply(lambda x: "🔥" if x else "")

# =========================
# PCR
# =========================
total_ce = df["CE OI"].sum()
total_pe = df["PE OI"].sum()

pcr = total_pe / total_ce if total_ce != 0 else 0

st.metric("📊 PCR", round(pcr, 2))

# =========================
# STRIKE FILTER
# =========================
min_strike, max_strike = st.slider(
    "Strike Range",
    int(df["Strike"].min()),
    int(df["Strike"].max()),
    (int(df["Strike"].min()), int(df["Strike"].max()))
)

df = df[(df["Strike"] >= min_strike) & (df["Strike"] <= max_strike)]

# =========================
# TABLE DISPLAY
# =========================
st.dataframe(
    df.style.format({
        "CE OI": "{:,.0f}",
        "PE OI": "{:,.0f}",
        "CE LTP": "{:.2f}",
        "PE LTP": "{:.2f}",
        "CE Delta": "{:.3f}",
        "PE Delta": "{:.3f}",
        "CE Theta": "{:.2f}",
        "PE Theta": "{:.2f}",
    }),
    use_container_width=True
)

# =========================
# OI CHART
# =========================
st.subheader("📊 OI Chart")

fig = px.bar(
    df,
    x="Strike",
    y=["CE OI", "PE OI"],
    barmode="group"
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# LTP CHART
# =========================
st.subheader("📈 LTP Chart")

chart_df = df[["Strike", "CE LTP", "PE LTP"]].set_index("Strike")

st.line_chart(chart_df)
