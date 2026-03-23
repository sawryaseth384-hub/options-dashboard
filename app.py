import sys
import os
import streamlit as st
import pandas as pd
import plotly.express as px

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain

st.set_page_config(page_title="🔥 Smart Options Dashboard", layout="wide")
st.title("🔥 Smart Options Dashboard")

# =========================
# SYMBOL
# =========================
symbol = st.text_input("Symbol", "NIFTY")
SECURITY_ID = 13

# =========================
# CACHE EXPIRY
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
    st.error("No expiry")
    st.stop()

expiry = st.selectbox("Expiry", expiry_list)

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

# =========================
# FETCH OPTION CHAIN
# =========================
@st.cache_data(ttl=300)
def fetch_chain(sec_id, exp):
    data = get_option_chain(sec_id, exp)
    if not data or "data" not in data:
        return {}
    inner = data["data"]
    if isinstance(inner, dict) and "data" in inner:
        inner = inner["data"]
    return inner

data = fetch_chain(SECURITY_ID, expiry)

spot = data.get("last_price", 0)
st.success(f"📍 Spot: {spot}")

oc = data.get("oc", {})

if not oc:
    st.error("No Option Chain Data")
    st.stop()

# =========================
# DATAFRAME
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
    st.error("No Data")
    st.stop()

df = df.sort_values("Strike")

# =========================
# PCR (FIXED POSITION)
# =========================
total_ce = df["CE OI"].sum()
total_pe = df["PE OI"].sum()
pcr = total_pe / total_ce if total_ce else 0

st.metric("📊 PCR", round(pcr, 2))

# =========================
# PRICE + OI CHANGE
# =========================
df["CE Price Change"] = df["CE LTP"].diff()
df["PE Price Change"] = df["PE LTP"].diff()
df["CE OI Change"] = df["CE OI"].diff()
df["PE OI Change"] = df["PE OI"].diff()

# =========================
# BUILD-UP LOGIC (UPGRADED)
# =========================
def buildup(row):
    if row["CE Price Change"] > 0 and row["CE OI Change"] > 0:
        return "🚀 CE Long"
    elif row["PE Price Change"] > 0 and row["PE OI Change"] > 0:
        return "🚀 PE Long"
    elif row["CE Price Change"] < 0 and row["CE OI Change"] > 0:
        return "📉 CE Short"
    elif row["PE Price Change"] < 0 and row["PE OI Change"] > 0:
        return "📉 PE Short"
    else:
        return ""

df["BuildUp"] = df.apply(buildup, axis=1)

# =========================
# ATM
# =========================
atm = min(df["Strike"], key=lambda x: abs(x - spot))
st.success(f"🎯 ATM: {atm}")

# =========================
# MARKET BIAS
# =========================
if pcr > 1:
    st.success("📈 Bullish Market")
elif pcr < 0.7:
    st.error("📉 Bearish Market")
else:
    st.warning("⚖️ Sideways Market")

# =========================
# SUPPORT / RESISTANCE
# =========================
resistance = df.nlargest(2, "CE OI")["Strike"].tolist()
support = df.nlargest(2, "PE OI")["Strike"].tolist()

st.error(f"🔴 Resistance: {resistance}")
st.success(f"🟢 Support: {support}")

# =========================
# MAX PAIN
# =========================
pain = []
for strike in df["Strike"]:
    val = (
        ((df["Strike"] - strike).clip(lower=0) * df["CE OI"]).sum() +
        ((strike - df["Strike"]).clip(lower=0) * df["PE OI"]).sum()
    )
    pain.append((strike, val))

max_pain = min(pain, key=lambda x: x[1])[0]
st.info(f"🎯 Max Pain: {max_pain}")

# =========================
# SMART STRIKE (DELTA BASED)
# =========================
best = df.iloc[(df["CE Delta"] - 0.5).abs().argsort()[:1]]
best_strike = int(best["Strike"].values[0])

st.info(f"🔥 Best Strike: {best_strike}")

# =========================
# FINAL SIGNAL (SMART)
# =========================
def final_signal(row):
    if pcr > 1 and row["CE Delta"] > 0.5:
        return "🟢 BUY CE"
    elif pcr < 0.7 and row["PE Delta"] < -0.5:
        return "🔴 BUY PE"
    return ""

df["Final Signal"] = df.apply(final_signal, axis=1)

# =========================
# STRIKE FILTER
# =========================
min_s, max_s = st.slider(
    "Strike Range",
    int(df["Strike"].min()),
    int(df["Strike"].max()),
    (int(df["Strike"].min()), int(df["Strike"].max()))
)

df = df[(df["Strike"] >= min_s) & (df["Strike"] <= max_s)]

# =========================
# TABLE (FIXED FORMAT)
# =========================
st.dataframe(
    df.style.format({
        "CE OI": "{:,.0f}",
        "PE OI": "{:,.0f}",
        "CE LTP": "{:.2f}",
        "PE LTP": "{:.2f}",
        "BuildUp": "{}",
        "Final Signal": "{}"
    }),
    use_container_width=True
)

# =========================
# OI CHART
# =========================
fig = px.bar(df, x="Strike", y=["CE OI", "PE OI"], barmode="group")
st.plotly_chart(fig, use_container_width=True)

# =========================
# LTP CHART (ENHANCED)
# =========================
atm_range = st.slider("ATM Range", 100, 1000, 300)

ltp_df = df[
    (df["Strike"] > spot - atm_range) &
    (df["Strike"] < spot + atm_range)
]

fig2 = px.line(
    ltp_df.melt(id_vars="Strike", value_vars=["CE LTP", "PE LTP"]),
    x="Strike",
    y="value",
    color="variable",
    markers=True
)

# ATM LINE
fig2.add_vline(x=atm, line_dash="dash", line_color="yellow")

st.plotly_chart(fig2, use_container_width=True)
