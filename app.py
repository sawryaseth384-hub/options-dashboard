import streamlit as st

# Dhan Modules
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain
from dhan_data.market_quote import get_ltp
from dhan_data.historical_data import get_historical
from dhan_data.debug import show_debug

from core.token_manager import get_token

# =========================
# PAGE
# =========================
st.set_page_config(layout="wide")
st.title("🚀 Dhan Trading Dashboard (FINAL)")

# =========================
# TOKEN
# =========================
token = get_token()
st.write(f"Token: {'✅' if token else '❌'}")

# =========================
# SYMBOLS
# =========================
symbols = {
    "NIFTY": (13, "IDX_I"),
    "RELIANCE": (2885, "NSE_EQ"),
}

nifty_sec, nifty_seg = symbols["NIFTY"]
rel_sec, rel_seg = symbols["RELIANCE"]

st.write("NIFTY:", nifty_sec, nifty_seg)
st.write("RELIANCE:", rel_sec, rel_seg)

# =========================
# OPTION CHAIN
# =========================
st.subheader("📊 Option Chain")

exp_list = get_expiry(nifty_sec, nifty_seg)

oc_ok = False

if exp_list:
    expiry = exp_list[0]
    oc = get_option_chain(nifty_sec, expiry, nifty_seg)

    if oc and "data" in oc:
        spot = oc["data"].get("last_price")
        st.write("Spot:", spot)
        oc_ok = True
    else:
        st.error("OC Failed")

# =========================
# LTP
# =========================
st.subheader("💰 Market Quote")

ltp = get_ltp(rel_sec, rel_seg)
st.write("RELIANCE LTP:", ltp)

# =========================
# HISTORICAL
# =========================
st.subheader("📈 Historical Data")

hist = get_historical(rel_sec, rel_seg)

if hist:
    st.success(f"Data Points: {len(hist['close'])}")
else:
    st.warning("No historical data")

# =========================
# DEBUG
# =========================
show_debug(token, ltp, hist, oc_ok)

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh"):
    st.rerun()

st.success("✅ Dashboard Running Stable")
