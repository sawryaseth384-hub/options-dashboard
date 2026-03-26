import streamlit as st

from core.dhan_v2 import (
    extract_ltp,
    get_depth,
    get_historical,
    get_intraday,
    get_ltp,
    get_option_chain,
)

st.set_page_config(layout="wide")
st.title("🚀 Dhan Trading Dashboard")

SECURITY_MAP = {
    "NIFTY": ("13", "NSE_INDEX"),
    "RELIANCE": ("2885", "NSE_EQ"),
}


def _extract_data_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "result", "records", "candles"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return None


symbol = st.selectbox("Select Symbol", list(SECURITY_MAP.keys()))
security_id, segment = SECURITY_MAP[symbol]

st.subheader("📈 Live Price")
ltp_data = get_ltp(security_id, segment)

if isinstance(ltp_data, dict) and "error" in ltp_data:
    st.error(ltp_data["error"])
else:
    ltp_value = extract_ltp(ltp_data)
    st.metric("LTP", "No Data" if ltp_value is None else f"{ltp_value:.2f}")

st.subheader("📊 Option Chain")
chain = get_option_chain(security_id)

if isinstance(chain, dict) and "error" in chain:
    st.error(chain["error"])
else:
    st.dataframe(chain, use_container_width=True)

st.subheader("📉 Intraday & Historical Data")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Intraday**")
    intraday_data = get_intraday(security_id, segment)
    if isinstance(intraday_data, dict) and "error" in intraday_data:
        st.error(intraday_data["error"])
    else:
        intraday_records = _extract_data_list(intraday_data)
        if intraday_records:
            st.dataframe(intraday_records, use_container_width=True)
        else:
            st.info("No intraday data available.")

with col2:
    st.markdown("**Historical**")
    historical_data = get_historical(security_id, segment)
    if isinstance(historical_data, dict) and "error" in historical_data:
        st.error(historical_data["error"])
    else:
        historical_records = _extract_data_list(historical_data)
        if historical_records:
            st.dataframe(historical_records, use_container_width=True)
        else:
            st.info("No historical data available.")

st.subheader("📘 Market Depth")
depth_data = get_depth(security_id, segment)

if isinstance(depth_data, dict) and "error" in depth_data:
    st.error(depth_data["error"])
else:
    st.json(depth_data)
