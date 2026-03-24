import streamlit as st
from dhan_data.instruments import get_symbol_data
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain
from dhan_data.market_quote import get_ltp
from dhan_data.historical_data import get_historical
from dhan_data.chart import get_candle_data, plot_candle
from dhan_data.live_market_feed import start_live_feed, subscribe_instrument, get_live_ltp
from dhan_data.depth_feed import start_depth_feed, subscribe_depth, get_depth
from core.token_manager import get_token
import pandas as pd

st.set_page_config(layout="wide")
st.title("🔬 Full Dhan Modules Scan")

# 1. Token
st.subheader("1. Token")
token = get_token()
st.write(f"Token: {'✅' if token else '❌'}")

# 2. Symbol resolution for all symbols
st.subheader("2. Symbol Resolution")
symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]
for sym in symbols:
    sec_id, seg = get_symbol_data(sym)
    if sec_id is None:
        # fallback
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
        sec_id, seg = HARD.get(sym, (None, None))
    st.write(f"{sym}: sec_id={sec_id}, segment={seg}")

# 3. Expiry list for NIFTY
st.subheader("3. Expiry List (NIFTY)")
nifty_sec, nifty_seg = get_symbol_data("NIFTY") or (13, "IDX_I")
exp_list = get_expiry(nifty_sec, nifty_seg)
st.write(f"NIFTY expiry list (first 5): {exp_list[:5] if exp_list else 'empty'}")

# 4. Option chain for NIFTY (first expiry)
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
        st.error(f"Option chain fetch failed: {oc_data}")

# 5. Live LTP
st.subheader("5. Live LTP (WebSocket)")
start_live_feed()
subscribe_instrument(nifty_sec, nifty_seg)
ltp = get_live_ltp()
st.write(f"Live LTP: {ltp} (should be non‑zero after a few seconds)")

# 6. Depth feed
st.subheader("6. Depth Feed")
start_depth_feed()
subscribe_depth(nifty_sec, nifty_seg)
depth = get_depth()
st.write(f"Depth bids: {depth['bids'][:2] if depth['bids'] else 'empty'}")
st.write(f"Depth asks: {depth['asks'][:2] if depth['asks'] else 'empty'}")

# 7. Historical data
st.subheader("7. Historical Data (5‑minute)")
hist = get_historical(nifty_sec, nifty_seg)
st.write(f"Historical data points: {len(hist) if hist else 0}")

# 8. Candlestick data
st.subheader("8. Candlestick Data")
candle_df = get_candle_data(nifty_sec, nifty_seg)
if candle_df is not None:
    st.write(f"Candles: {len(candle_df)}")
    st.dataframe(candle_df.tail(5))
else:
    st.error("Candlestick data returned None")

# 9. Market quote (static LTP)
st.subheader("9. Market Quote (static LTP)")
ltp_static = get_ltp(nifty_sec, nifty_seg)
st.write(f"Static LTP: {ltp_static}")

st.info("Scan complete. Scroll up to see all results.")
