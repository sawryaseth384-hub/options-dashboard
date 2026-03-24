import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from dhan_data.instruments import get_symbol_data
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain
from dhan_data.market_quote import get_ltp

st.set_page_config(layout="wide")

# =========================
# UI STYLE (CLEAN PRO)
# =========================
st.markdown("""
<style>
body {background-color:#0A0F18;color:white;}
.block-container {padding-top:1rem;}
div[data-testid="metric-container"]{
background:#111827;border-radius:10px;padding:10px;border:1px solid #1F2937;}
</style>
""", unsafe_allow_html=True)

st.title("🧠 Smart Money Options Dashboard")

# =========================
# SESSION
# =========================
if "prev_df" not in st.session_state:
    st.session_state.prev_df = None

# =========================
# SYMBOL
# =========================
symbol = st.sidebar.text_input("Symbol", "NIFTY").upper()

HARDCODED = {
    "NIFTY": (13, "IDX_I"),
    "BANKNIFTY": (25, "IDX_I"),
    "FINNIFTY": (27, "IDX_I"),
}

sec_id, seg = get_symbol_data(symbol)
if sec_id is None:
    sec_id, seg = HARDCODED.get(symbol, (None, None))

if sec_id is None:
    st.error("Invalid Symbol")
    st.stop()

# =========================
# EXPIRY
# =========================
exp = get_expiry(sec_id)
expiry_list = exp if isinstance(exp, list) else exp.get("data", [])

if not expiry_list:
    st.error("No Expiry")
    st.stop()

expiry = st.sidebar.selectbox("Expiry", expiry_list)

# =========================
# FETCH DATA
# =========================
@st.cache_data(ttl=60)
def fetch():
    return get_option_chain(sec_id, expiry, seg)

data = fetch()

if not data or "data" not in data:
    st.error("No Data")
    st.stop()

raw = data["data"]
spot = raw.get("last_price", 0)
oc = raw.get("oc", {})

# =========================
# HEADER (SLIM)
# =========================
colh1, colh2 = st.columns(2)
colh1.metric("NIFTY", f"{get_ltp(13,'IDX_I'):.2f}")
colh2.metric("BANKNIFTY", f"{get_ltp(25,'IDX_I'):.2f}")

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
# CHANGES
# =========================
prev = st.session_state.prev_df

if prev is not None:
    df["CE OI Change"] = df["CE OI"] - prev["CE OI"]
    df["PE OI Change"] = df["PE OI"] - prev["PE OI"]
else:
    df["CE OI Change"] = 0
    df["PE OI Change"] = 0

st.session_state.prev_df = df.copy()

# =========================
# METRICS
# =========================
pcr = df["PE OI"].sum() / df["CE OI"].sum()
atm = df.iloc[(df["Strike"] - spot).abs().argsort()[0]]["Strike"]

support = df.nlargest(2, "PE OI")["Strike"].tolist()
resistance = df.nlargest(2, "CE OI")["Strike"].tolist()

# =========================
# DECISION BAR
# =========================
col = st.columns(6)
col[0].metric("Spot", round(spot,2))
col[1].metric("PCR", round(pcr,2))
col[2].metric("ATM", atm)
col[3].metric("Bias", "Bullish" if pcr>1 else "Bearish")
col[4].metric("Signal", "BUY CE" if pcr>1 else "BUY PE")
col[5].metric("Strength", "Strong" if pcr>1.2 or pcr<0.8 else "Normal")

# =========================
# LEVELS
# =========================
col2 = st.columns(3)
col2[0].success(f"Support: {support}")
col2[1].error(f"Resistance: {resistance}")
col2[2].info(f"Max Pain: {atm}")

# =========================
# TABLE
# =========================
st.subheader("Option Chain")
st.dataframe(df, use_container_width=True)

# =========================
# CHARTS
# =========================
c1,c2 = st.columns(2)

with c1:
    fig = px.bar(df,x="Strike",y=["CE OI","PE OI"])
    fig.add_vline(x=spot,line_color="yellow")
    st.plotly_chart(fig,use_container_width=True)

with c2:
    fig2 = px.line(df,x="Strike",y=["CE LTP","PE LTP"])
    fig2.add_vline(x=spot,line_color="yellow")
    st.plotly_chart(fig2,use_container_width=True)

# =========================
# STRIKE ANALYSIS
# =========================
st.subheader("Strike Analysis")

strike = st.selectbox("Strike",df["Strike"])
row = df[df["Strike"]==strike].iloc[0]

st.write(row)

# =========================
# FOOTER
# =========================
st.markdown("DATA: DHAN | FINAL VERSION")
