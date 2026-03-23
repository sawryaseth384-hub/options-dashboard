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
    inner = data.get("data", {})
    if isinstance(inner, dict) and "data" in inner:
        inner = inner["data"]
    return inner

data = fetch_chain(SECURITY_ID, expiry)

spot = data.get("last_price", 0)
st.success(f"📍 Spot: {spot}")

oc = data.get("oc", {})

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

df = pd.DataFrame(rows).sort_values("Strike")
# =========================
# PRICE CHANGE (IMPORTANT)
# =========================
df["CE Price Change"] = df["CE LTP"].diff()
df["PE Price Change"] = df["PE LTP"].diff()

df["CE OI Change"] = df["CE OI"].diff()
df["PE OI Change"] = df["PE OI"].diff()

# =========================
# BUILD-UP LOGIC
# =========================
def get_signal(row):
    if row["CE Price Change"] > 0 and row["CE OI Change"] > 0:
        return "🚀 CE Long Build-up"
    elif row["PE Price Change"] > 0 and row["PE OI Change"] > 0:
        return "🚀 PE Long Build-up"
    elif row["CE Price Change"] < 0 and row["CE OI Change"] > 0:
        return "📉 CE Short Build-up"
    elif row["PE Price Change"] < 0 and row["PE OI Change"] > 0:
        return "📉 PE Short Build-up"
    else:
        return ""

df["BuildUp"] = df.apply(get_signal, axis=1)
# =========================
# FINAL TRADE SIGNAL
# =========================
df["Final Signal"] = df.apply(lambda x:
    "🟢 BUY CE" if pcr > 1 and x["CE Delta"] > 0.5 else
    "🔴 BUY PE" if pcr < 0.7 and x["PE Delta"] < -0.5 else
    "",
axis=1)

# =========================
# ATM
# =========================
atm = min(df["Strike"], key=lambda x: abs(x - spot))
st.success(f"🎯 ATM: {atm}")

# =========================
# PCR
# =========================
total_ce = df["CE OI"].sum()
total_pe = df["PE OI"].sum()
pcr = total_pe / total_ce if total_ce else 0

st.metric("📊 PCR", round(pcr, 2))

# =========================
# MARKET BIAS
# =========================
if pcr > 1:
    st.success("📈 Bullish")
elif pcr < 0.7:
    st.error("📉 Bearish")
else:
    st.warning("⚖️ Sideways")

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
pain_list = []

for strike in df["Strike"]:
    pain = (
        ((df["Strike"] - strike).clip(lower=0) * df["CE OI"]).sum() +
        ((strike - df["Strike"]).clip(lower=0) * df["PE OI"]).sum()
    )
    pain_list.append((strike, pain))

max_pain = min(pain_list, key=lambda x: x[1])[0]
st.info(f"🎯 Max Pain: {max_pain}")

# =========================
# SMART STRIKE
# =========================
best_strike = df.loc[df["CE Delta"].sub(0.5).abs().idxmin(), "Strike"]
st.info(f"🔥 Best Strike: {best_strike}")

# =========================
# BUILD-UP + TRAP
# =========================
df["CE BuildUp"] = df["CE OI"] > df["CE OI"].shift(1)
df["PE BuildUp"] = df["PE OI"] > df["PE OI"].shift(1)

df["Trap"] = df.apply(lambda x:
    "⚠️ Call Trap" if x["CE OI"] > x["PE OI"] and pcr < 0.7 else
    "⚠️ Put Trap" if x["PE OI"] > x["CE OI"] and pcr > 1 else "",
axis=1)

# =========================
# SIGNAL SYSTEM
# =========================
df["Signal"] = df.apply(lambda x:
    "🟢 BUY CE" if x["CE Delta"] > 0.5 and pcr > 1 else
    "🔴 BUY PE" if x["PE Delta"] < -0.5 and pcr < 0.7 else "",
axis=1)

# =========================
# FILTER
# =========================
min_s, max_s = st.slider(
    "Strike Range",
    int(df["Strike"].min()),
    int(df["Strike"].max()),
    (int(df["Strike"].min()), int(df["Strike"].max()))
)

df = df[(df["Strike"] >= min_s) & (df["Strike"] <= max_s)]

# =========================
# TABLE
# =========================
st.dataframe(
    df.style.format({
        "CE OI": "{:,.0f}",
        "PE OI": "{:,.0f}",
        "CE LTP": "{:.2f}",
        "PE LTP": "{:.2f}",
    }),
    use_container_width=True
)


# =========================
# OI CHART
# =========================
fig = px.bar(df, x="Strike", y=["CE OI", "PE OI"], barmode="group")
st.plotly_chart(fig, use_container_width=True)

# =========================
# LTP CHART
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

fig2.add_vline(x=atm, line_dash="dash", line_color="yellow")

st.plotly_chart(fig2, use_container_width=True)
