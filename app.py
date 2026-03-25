import streamlit as st
import pandas as pd

# Dhan Modules
from dhan_data.instruments import get_symbol_data
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain
from dhan_data.market_quote import get_ltp
from dhan_data.historical_data import get_historical
from dhan_data.chart import get_candle_data, plot_candle

from core.token_manager import get_token

# =========================
# PAGE SETUP
# =========================
st.set_page_config(layout="wide")
st.title("🔬 Full Dhan Modules Scan")

# =========================
# 1. TOKEN
# =========================
st.subheader("1. Token")
token = get_token()
st.write(f"Token: {'✅' if token else '❌'}")

# =========================
# 2. SYMBOL SETUP
# =========================
st.subheader("2. Symbol Resolution")

symbols = {
    "NIFTY": (13, "IDX_I"),
    "RELIANCE": (2885, "NSE_EQ"),
    "TCS": (11536, "NSE_EQ"),
    "HDFCBANK": (1333, "NSE_EQ"),
}

for sym, (sec, seg) in symbols.items():
    st.write(f"{sym}: sec_id={sec}, segment={seg}")

nifty_sec, nifty_seg = symbols["NIFTY"]

# =========================
# 3. EXPIRY LIST
# =========================
st.subheader("3. Expiry List (NIFTY)")
exp_list = get_expiry(nifty_sec, nifty_seg)

if exp_list:
    st.write(exp_list[:5])
else:
    st.warning("No expiry data")

# =========================
# 4. OPTION CHAIN
# =========================
st.subheader("4. Option Chain")

if exp_list:
    expiry = exp_list[0]
    oc_data = get_option_chain(nifty_sec, expiry, nifty_seg)

    if oc_data and "data" in oc_data:
        spot = oc_data["data"].get("last_price")
        oc = oc_data["data"].get("oc", {})
        strikes = sorted([int(float(s)) for s in oc.keys()])

        st.write(f"Spot: {spot}")
        st.write(f"Strikes Count: {len(strikes)}")
    else:
        st.error("Option Chain Failed")

# =========================
# 5. MARKET QUOTES (FIXED)
# =========================
st.subheader("5. Market Quotes")

quote_list = [
    ("RELIANCE", 2885, "NSE_EQ"),  # 🔴 अभी 1 ही रखो (429 avoid)
]

data = []

for name, sec, seg in quote_list:
    ltp = get_ltp(sec, seg)
    data.append({
        "Symbol": name,
        "LTP": ltp
    })

st.dataframe(pd.DataFrame(data))

# =========================
# 6. HISTORICAL (FIXED)
# =========================
st.subheader("6. Historical Data")

hist = get_historical(2885, "NSE_EQ")  # 🔴 IDX मत use करो

if hist:
    st.success("Historical Loaded")
    st.write(hist)  # debug
else:
    st.warning("No historical data")

# =========================
# 7. CANDLE (FIXED)
# =========================
st.subheader("7. Candlestick")

df = get_candle_data(2885, "NSE_EQ")

if df is not None and len(df) > 0:
    fig, trend = plot_candle(df)
    st.write(f"Trend: {trend}")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No candle data")

# =========================
# REFRESH
# =========================
if st.button("Refresh"):
    st.cache_data.clear()
    st.rerun()

st.success("✅ Scan Complete")
