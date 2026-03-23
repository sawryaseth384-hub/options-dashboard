import sys
import os
import streamlit as st
import pandas as pd
import plotly.express as px

# Fix import
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

# =========================
# SESSION STATE (ATM FIX)
# =========================
if "atm_mode" not in st.session_state:
    st.session_state.atm_mode = False

# =========================
# FETCH EXPIRY (CACHE)
# =========================
@st.cache_data(ttl=3600)
def fetch_expiry(sec_id):
    data = get_expiry(sec_id)
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "data" in data:
        return data["data"]
    return []

expiry_list = fetch_expiry(SECURITY_ID)

if not expiry_list:
    st.error("❌ No expiry data")
    st.stop()

expiry = st.selectbox("Select Expiry", expiry_list)

# =========================
# REFRESH BUTTON
# =========================
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# =========================
# FETCH OPTION CHAIN (CACHE)
# =========================
@st.cache_data(ttl=300)
def fetch_option_chain(sec_id, exp):
    data = get_option_chain(sec_id, exp)
    if not data or "data" not in data:
        return {"error": "Invalid API"}
    inner = data["data"]
    if isinstance(inner, dict) and "data" in inner:
        inner = inner["data"]
    return inner

oc_data = fetch_option_chain(SECURITY_ID, expiry)

if "error" in oc_data:
    st.error(oc_data["error"])
    st.stop()

spot = oc_data.get("last_price", 0)
st.success(f"📍 Spot Price: {spot}")

oc = oc_data.get("oc", {})
if not oc:
    st.error("❌ No option chain data")
    st.stop()

# =========================
# BUILD DATAFRAME
# =========================
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

df = pd.DataFrame(rows)

if df.empty:
    st.error("❌ No data")
    st.stop()

df = df.sort_values("Strike")

# =========================
# ATM STRIKE
# =========================
atm_strike = min(df["Strike"], key=lambda x: abs(x - spot))
st.success(f"🎯 Suggested ATM Strike: {atm_strike}")

df["ATM"] = df["Strike"].apply(lambda x: "🎯" if x == atm_strike else "")

# =========================
# PCR
# =========================
total_ce = df["CE OI"].sum()
total_pe = df["PE OI"].sum()

pcr = total_pe / total_ce if total_ce else 0
st.metric("📊 PCR", round(pcr, 2))

# =========================
# ATM PCR
# =========================
atm_df = df[(df["Strike"] > spot - 100) & (df["Strike"] < spot + 100)]

atm_ce = atm_df["CE OI"].sum()
atm_pe = atm_df["PE OI"].sum()

atm_pcr = atm_pe / atm_ce if atm_ce else 0
st.metric("🎯 ATM PCR", round(atm_pcr, 2))

# =========================
# SUPPORT / RESISTANCE
# =========================
top_ce = df.nlargest(2, "CE OI")["Strike"].tolist()
top_pe = df.nlargest(2, "PE OI")["Strike"].tolist()

st.error(f"🔴 Resistance: {top_ce}")
st.success(f"🟢 Support: {top_pe}")

# =========================
# MAX PAIN
# =========================
pain_data = []

for strike in df["Strike"]:
    pain = (
        ((df["Strike"] - strike).clip(lower=0) * df["CE OI"]).sum() +
        ((strike - df["Strike"]).clip(lower=0) * df["PE OI"]).sum()
    )
    pain_data.append((strike, pain))

max_pain = min(pain_data, key=lambda x: x[1])[0]
st.info(f"🎯 Max Pain: {max_pain}")

# =========================
# STRIKE FILTER
# =========================
min_strike, max_strike = st.slider(
    "Strike Range",
    int(df["Strike"].min()),
    int(df["Strike"].max()),
    (int(df["Strike"].min()), int(df["Strike"].max()))
)

filtered_df = df[(df["Strike"] >= min_strike) & (df["Strike"] <= max_strike)]

# =========================
# ATM MODE BUTTON (FIXED)
# =========================
if st.button("🎯 Focus ATM"):
    st.session_state.atm_mode = not st.session_state.atm_mode

if st.session_state.atm_mode:
    filtered_df = df[
        (df["Strike"] > spot - 300) &
        (df["Strike"] < spot + 300)
    ]

# =========================
# TABLE
# =========================
st.dataframe(
    filtered_df.style.format({
        "CE OI": "{:,.0f}",
        "PE OI": "{:,.0f}",
        "CE LTP": "{:.2f}",
        "PE LTP": "{:.2f}",
        "CE Delta": "{:.3f}",
        "PE Delta": "{:.3f}",
    }),
    use_container_width=True
)

# =========================
# OI CHART
# =========================
st.subheader("📊 OI Chart")

fig_oi = px.bar(
    filtered_df,
    x="Strike",
    y=["CE OI", "PE OI"],
    barmode="group"
)

st.plotly_chart(fig_oi, use_container_width=True)

# =========================
# LTP CHART (FIXED)
# =========================
st.subheader("📈 LTP Chart")

atm_range_slider = st.slider("ATM Range", 100, 1000, 500, step=50)

ltp_df = filtered_df[
    (filtered_df["Strike"] > spot - atm_range_slider) &
    (filtered_df["Strike"] < spot + atm_range_slider)
]

if not ltp_df.empty:
    fig_ltp = px.line(
        ltp_df.melt(id_vars="Strike", value_vars=["CE LTP", "PE LTP"]),
        x="Strike",
        y="value",
        color="variable"
    )
    st.plotly_chart(fig_ltp, use_container_width=True)
else:
    st.warning("No data in selected range")
