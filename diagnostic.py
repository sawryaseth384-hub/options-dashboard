import streamlit as st
from dhan_data.instruments import get_symbol_data
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain
from dhan_data.market_quote import get_ltp
from core.token_manager import get_token, get_headers

st.set_page_config(layout="wide")
st.title("🔬 Full System Diagnostic")

# 1. Token test
st.header("1. Token")
token = get_token()
st.write(f"Token generated: {token is not None}")

# 2. Symbol resolution
st.header("2. Symbol Resolution")
symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]
symbol_data = {}
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
    symbol_data[sym] = (sec_id, seg)
    st.write(f"{sym}: sec_id={sec_id}, segment={seg}")

# 3. Expiry lists
st.header("3. Expiry Lists (first 3)")
for sym, (sec_id, seg) in symbol_data.items():
    if sec_id:
        try:
            expiry_list = get_expiry(sec_id, seg)
            st.write(f"{sym}: {expiry_list[:3] if expiry_list else 'empty'}")
        except Exception as e:
            st.error(f"{sym}: error - {e}")
    else:
        st.error(f"{sym}: no sec_id")

# 4. Option chain for the first expiry
st.header("4. Option Chain Sample (first expiry)")
for sym, (sec_id, seg) in symbol_data.items():
    if sec_id:
        expiry_list = get_expiry(sec_id, seg)
        if expiry_list:
            expiry = expiry_list[0]
            data = get_option_chain(sec_id, expiry, seg)
            if data and "data" in data:
                spot = data["data"].get("last_price")
                oc = data["data"].get("oc", {})
                strikes = sorted([int(float(s)) for s in oc.keys()])
                st.write(f"**{sym}** expiry {expiry} → spot={spot}, strikes={len(strikes)}")
                if strikes:
                    # show first 5 and last 5 strikes (to see if ATM is included)
                    st.write(f"  First 5 strikes: {strikes[:5]}")
                    st.write(f"  Last 5 strikes: {strikes[-5:]}")
                    # also show a few strikes around the spot (if spot is available)
                    if spot:
                        near = [s for s in strikes if abs(s - spot) <= 500]
                        if near:
                            st.write(f"  Strikes near spot {spot}: {near[:5]}")
                    # check if any strike has non-zero OI
                    sample_strike = strikes[0]
                    ce_oi = oc[str(sample_strike)]['ce'].get('oi', 0)
                    pe_oi = oc[str(sample_strike)]['pe'].get('oi', 0)
                    st.write(f"  Sample strike {sample_strike}: CE OI={ce_oi}, PE OI={pe_oi}")
                else:
                    st.warning("No strikes in option chain.")
            else:
                st.error(f"{sym}: option chain fetch failed - {data}")
        else:
            st.warning(f"{sym}: no expiry list")
    else:
        st.error(f"{sym}: no sec_id")

# 5. Live LTP test (optional)
st.header("5. Live LTP (if available)")
try:
    from dhan_data.live_market_feed import get_live_ltp
    ltp = get_live_ltp()
    st.write(f"Live LTP: {ltp}")
except Exception as e:
    st.warning(f"Live feed not available: {e}")

st.info("Diagnostic complete. Scroll up to see all results.")
