import streamlit as st
from core import dhan_api
import pandas as pd
import plotly.graph_objects as go

# =========================
# 🔥 PAGE CONFIG
# =========================
st.set_page_config(page_title="🔥 Dhan Full System", layout="wide")
st.title("📈 Dhan AI Full Options Dashboard")

# =========================
# 🎯 SYMBOL INPUT
# =========================
symbol = st.text_input(
    "Enter Symbol (NIFTY / BANKNIFTY / RELIANCE / SBIN)",
    value="NIFTY"
)

if not symbol:
    st.stop()

# =========================
# 🚀 FETCH FULL DATA
# =========================
data = dhan_api.get_full_data(symbol)

if "error" in data:
    st.error(data["error"])
    st.stop()

# =========================
# 📊 BASIC INFO
# =========================
col1, col2, col3 = st.columns(3)

col1.metric("Symbol", data["symbol"])
col2.metric("Spot (LTP)", data["ltp"])
col3.metric("Segment", data["segment"])

st.caption(f"Security ID: {data['security_id']}")

# =========================
# 📅 EXPIRY SELECT
# =========================
expiry = None
if data["expiries"]:
    expiry = st.selectbox("Select Expiry", data["expiries"])
else:
    st.warning("No expiry data available")

# =========================
# 📊 OPTION CHAIN
# =========================
st.markdown("## 📊 Option Chain")

if expiry:
    option_data = dhan_api.fetch_option_chain(
        data["security_id"],
        data["segment"],
        expiry
    )

    if option_data and "data" in option_data:
        oc = option_data["data"].get("oc", {})

        rows = []

        for strike, val in oc.items():
            ce = val.get("ce", {})
            pe = val.get("pe", {})

            rows.append({
                "Strike": float(strike),
                "Call OI": ce.get("oi", 0),
                "Call LTP": ce.get("last_price", 0),
                "Put OI": pe.get("oi", 0),
                "Put LTP": pe.get("last_price", 0)
            })

        df = pd.DataFrame(rows).sort_values("Strike")

        st.dataframe(df, use_container_width=True)

    else:
        st.warning("No option chain data")

# =========================
# 📈 HISTORICAL CHART
# =========================
st.markdown("## 📈 Price Chart")

hist = data["historical"]

if hist:
    df = pd.DataFrame(hist)

    fig = go.Figure(data=[go.Candlestick(
        x=df["time"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"]
    )])

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("No historical data")

# =========================
# 📦 EXPIRED OPTIONS
# =========================
st.markdown("## 📦 Expired Options")

expired = data["expired"]

if expired:
    st.json(expired)
else:
    st.warning("No expired options data")

# =========================
# 🔍 DEBUG PANEL
# =========================
with st.expander("🔍 Debug Info"):
    st.json(data)
