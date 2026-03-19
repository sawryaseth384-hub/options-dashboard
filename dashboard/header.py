import streamlit as st

def show_header(data):

    idx = data["indices"]
    glb = data["global"]
    cmd = data["commodities"]
    cur = data["currency"]

    # 🔥 LINE 1
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("NIFTY", idx["nifty"]["ltp"], idx["nifty"]["change"])
    col2.metric("BANKNIFTY", idx["banknifty"]["ltp"], idx["banknifty"]["change"])
    col3.metric("SENSEX", idx["sensex"]["ltp"], idx["sensex"]["change"])
    col4.metric("VIX", idx["vix"]["ltp"], idx["vix"]["change"])

    # 🔥 LINE 2
    col5, col6, col7, col8 = st.columns(4)

    col5.metric("DOW", glb["dow"]["ltp"], glb["dow"]["change"])
    col6.metric("NASDAQ", glb["nasdaq"]["ltp"], glb["nasdaq"]["change"])
    col7.metric("GIFT", glb["gift"]["ltp"], glb["gift"]["change"])
    col8.metric("CRUDE", cmd["crude"]["ltp"], cmd["crude"]["change"])

    # 🔥 LINE 3
    col9, col10, col11, col12 = st.columns(4)

    col9.metric("GOLD", cmd["gold"]["ltp"], cmd["gold"]["change"])
    col10.metric("SILVER", cmd["silver"]["ltp"], cmd["silver"]["change"])
    col11.metric("USDINR", cur["usd"]["ltp"], cur["usd"]["change"])
    col12.metric("DXY", cur["dxy"]["ltp"], cur["dxy"]["change"])
