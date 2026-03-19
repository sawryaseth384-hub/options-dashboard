import streamlit as st

def item(name, ltp, change):
    color = "#00c853" if change >= 0 else "#ff1744"
    arrow = "▲" if change >= 0 else "▼"

    return f"""
    <span style='margin-right:25px; font-size:13px; color:#ccc'>
        <b style='color:white'>{name}</b> {ltp}
        <span style='color:{color}'> {arrow} {change}</span>
    </span>
    """

def show_header(data):

    idx = data["indices"]
    glb = data["global"]
    cmd = data["commodities"]
    cur = data["currency"]

    line1 = (
        item("NIFTY", idx["nifty"]["ltp"], idx["nifty"]["change"]) +
        item("BANKNIFTY", idx["banknifty"]["ltp"], idx["banknifty"]["change"]) +
        item("SENSEX", idx["sensex"]["ltp"], idx["sensex"]["change"]) +
        item("VIX", idx["vix"]["ltp"], idx["vix"]["change"])
    )

    line2 = (
        item("DOW", glb["dow"]["ltp"], glb["dow"]["change"]) +
        item("NASDAQ", glb["nasdaq"]["ltp"], glb["nasdaq"]["change"]) +
        item("GIFT", glb["gift"]["ltp"], glb["gift"]["change"]) +
        item("CRUDE", cmd["crude"]["ltp"], cmd["crude"]["change"]) +
        item("GOLD", cmd["gold"]["ltp"], cmd["gold"]["change"]) +
        item("SILVER", cmd["silver"]["ltp"], cmd["silver"]["change"]) +
        item("USDINR", cur["usd"]["ltp"], cur["usd"]["change"]) +
        item("DXY", cur["dxy"]["ltp"], cur["dxy"]["change"])
    )

    st.markdown("""
    <style>
    .strip {
        background:#0E1117;
        padding:8px 15px;
        border-radius:8px;
        margin-bottom:5px;
        white-space:nowrap;
        overflow-x:auto;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"<div class='strip'>{line1}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='strip'>{line2}</div>", unsafe_allow_html=True)
