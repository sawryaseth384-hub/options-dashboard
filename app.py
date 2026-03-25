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

try:
    exp_list = get_expiry(nifty_sec, nifty_seg)
    if exp_list:
        st.write(exp_list[:5])
    else:
        st.warning("No expiry data")
except Exception as e:
    st.error(f"Expiry Error: {e}")

# =========================
# 4. OPTION CHAIN
# =========================
st.subheader("4. Option Chain")

try:
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
            st.warning("Option Chain Empty")
except Exception as e:
    st.error(f"Option Chain Error: {e}")

# =========================
# 5. MARKET QUOTES
# =========================
st.subheader("5. Market Quotes")

try:
    quote_data = []

    for name, (sec, seg) in symbols.items():
        ltp = get_ltp(sec, seg)
        quote_data.append({
            "Symbol": name,
            "LTP": ltp
        })

    df = pd.DataFrame(quote_data)
    st.dataframe(df)

except Exception as e:
    st.error(f"LTP Error: {e}")

# =========================
# 6. HISTORICAL DATA
# =========================
st.subheader("6. Historical Data")

try:
    hist = get_historical(2885, "NSE_EQ")

    if hist and len(hist.get("close", [])) > 0:
        st.success(f"Data Points: {len(hist.get('close', []))}")
    else:
        st.warning("No historical data")

except Exception as e:
    st.error(f"Historical Error: {e}")

# =========================
# 7. CANDLESTICK
# =========================
st.subheader("7. Candlestick")

try:
    df = get_candle_data(2885, "NSE_EQ")

    if df is not None and len(df) > 1:
        fig, trend = plot_candle(df)
        st.write(f"Trend: {trend}")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No candle data")

except Exception as e:
    st.error(f"Candle Error: {e}")

# =========================
# 🔍 DEBUG PANEL (IMPORTANT)
# =========================
st.subheader("🛠 DEBUG PANEL")

# TOKEN
try:
    token = get_token()
    st.success("✅ Token OK")
except Exception as e:
    st.error(f"❌ Token Error: {e}")

# LTP
try:
    test_ltp = get_ltp(2885, "NSE_EQ")
    if test_ltp:
        st.success(f"✅ LTP OK: {test_ltp}")
    else:
        st.warning("⚠️ LTP Zero")
except Exception as e:
    st.error(f"❌ LTP Error: {e}")

# OPTION CHAIN
try:
    exp = get_expiry(13, "IDX_I")
    if exp:
        oc = get_option_chain(13, exp[0], "IDX_I")
        if oc:
            st.success("✅ Option Chain OK")
        else:
            st.warning("⚠️ OC Empty")
    else:
        st.warning("⚠️ Expiry Empty")
except Exception as e:
    st.error(f"❌ Option Chain Error: {e}")

# HISTORICAL
try:
    hist = get_historical(2885, "NSE_EQ")
    if hist and len(hist.get("close", [])) > 0:
        st.success("✅ Historical OK")
    else:
        st.warning("⚠️ No Historical Data")
except Exception as e:
    st.error(f"❌ Historical Error: {e}")

# CANDLE
try:
    df = get_candle_data(2885, "NSE_EQ")
    if df is not None and len(df) > 1:
        st.success("✅ Candle OK")
    else:
        st.warning("⚠️ Candle Not Enough Data")
except Exception as e:
    st.error(f"❌ Candle Error: {e}")

# =========================
# REFRESH
# =========================
if st.button("Refresh"):
    st.cache_data.clear()
    st.rerun()

st.success("✅ Scan Complete")
