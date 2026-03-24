import streamlit as st
import pandas as pd
import time

from dhan_data.instruments import get_symbol_data
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain
from dhan_data.market_quote import get_ltp
from dhan_data.historical_data import get_historical
from dhan_data.chart import get_candle_data, plot_candle

# WebSocket
from dhan_data.live_market_feed import start_live_feed, subscribe_instrument, get_live_ltp
from dhan_data.depth_feed import start_depth_feed, subscribe_depth, get_depth

from core.token_manager import get_token

st.set_page_config(layout="wide")
st.title("🔬 Full Dhan Modules Scan")

# =========================
# 1. TOKEN
# =========================
st.subheader("1. Token")
token = get_token()
st.write(f"Token: {'✅' if token else '❌'}")

# =========================
# 2. SYMBOL RESOLUTION
# =========================
st.subheader("2. Symbol Resolution")

symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]

HARD = {
    "NIFTY": (13, "IDX_I"),
    "BANKNIFTY": (25, "IDX_I"),
    "FINNIFTY": (27, "IDX_I"),
    "RELIANCE": (2885, "NSE_FNO"),
    "TCS": (11536, "NSE_FNO"),
    "HDFCBANK": (1333, "NSE_FNO"),
    "INFY": (4083, "NSE_FNO"),
    "ICICIBANK": (495, "NSE_FNO"),
}

symbol_map = {}

for sym in symbols:
    sec_id, seg = get_symbol_data(sym)
    if sec_id is None:
        sec_id, seg = HARD.get(sym, (None, None))

    symbol_map[sym] = (sec_id, seg)
    st.write(f"{sym}: sec_id={sec_id}, segment={seg}")

# Use NIFTY for test
nifty_sec, nifty_seg = symbol_map["NIFTY"]

# =========================
# 3. EXPIRY
# =========================
st.subheader("3. Expiry List (NIFTY)")
exp_list = get_expiry(nifty_sec, nifty_seg)

st.write(f"NIFTY expiry list (first 5): {exp_list[:5] if exp_list else 'empty'}")

# =========================
# 4. OPTION CHAIN
# =========================
st.subheader("4. Option Chain (NIFTY, first expiry)")

if exp_list:
    expiry = exp_list[0]
    oc_data = get_option_chain(nifty_sec, expiry, nifty_seg)

    if oc_data and "data" in oc_data:
        spot = oc_data["data"].get("last_price")
        oc = oc_data["data"].get("oc", {})

        strikes = sorted([int(float(s)) for s in oc.keys()])

        st.write(f"Expiry {expiry}: spot={spot}, strikes={len(strikes)}")
        st.write(f"First 5 strikes: {strikes[:5]}, Last 5: {strikes[-5:]}")
    else:
        st.error("Option chain fetch failed")

# =========================
# 5. LIVE LTP (WS)
# =========================
st.subheader("5. Live LTP (WebSocket)")

start_live_feed()
subscribe_instrument(nifty_sec, nifty_seg)

time.sleep(2)

ltp_live = get_live_ltp()
st.write(f"Live LTP: {ltp_live}")

# =========================
# 6. DEPTH FEED (WS)
# =========================
st.subheader("6. Depth Feed (Bid/Ask)")

start_depth_feed()
subscribe_depth(nifty_sec, nifty_seg)

time.sleep(3)

depth = get_depth()

if depth["bids"] or depth["asks"]:
    st.success("✅ Depth data received")

    col1, col2 = st.columns(2)

    with col1:
        st.write("📉 Bids")
        st.dataframe(pd.DataFrame(depth["bids"][:5]))

    with col2:
        st.write("📈 Asks")
        st.dataframe(pd.DataFrame(depth["asks"][:5]))

else:
    st.warning("❌ No depth data yet")

# =========================
# 7. HISTORICAL DATA
# =========================
st.subheader("7. Historical Data (5-minute)")

hist = get_historical(nifty_sec, nifty_seg)

if hist:
    st.write(f"Historical data points: {len(hist)}")
else:
    st.warning("No historical data")

# =========================
# 8. CANDLESTICK
# =========================
st.subheader("8. Candlestick Data")

candle_df = get_candle_data(nifty_sec, nifty_seg)

if candle_df is not None:
    st.success(f"Candles: {len(candle_df)}")

    fig, trend = plot_candle(candle_df)

    st.write(f"Trend: {trend}")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Candlestick data returned None")

# =========================
# 9. STATIC LTP
# =========================
st.subheader("9. Market Quote (static LTP)")

ltp_static = get_ltp(nifty_sec, nifty_seg)
st.write(f"Static LTP: {ltp_static}")

st.success("✅ Scan complete")
