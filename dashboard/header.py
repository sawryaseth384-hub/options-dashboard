import streamlit as st

def show_header(data):

    html = f"""
    <div style='
        background:#0b1220;
        padding:10px 18px;
        border-radius:8px;
        margin-bottom:10px;
        overflow-x:auto;
        white-space:nowrap;
    '>

    <span style='margin-right:22px; font-size:13px; color:#bbb'>
        <b style='color:white'>NIFTY</b> {data["NIFTY"]["ltp"]}
        <span style='color:#00c853'> ▲ {data["NIFTY"]["change"]}</span>
    </span>

    <span style='margin-right:22px; font-size:13px; color:#bbb'>
        <b style='color:white'>BANKNIFTY</b> {data["BANKNIFTY"]["ltp"]}
        <span style='color:#00c853'> ▲ {data["BANKNIFTY"]["change"]}</span>
    </span>

    <span style='margin-right:22px; font-size:13px; color:#bbb'>
        <b style='color:white'>SENSEX</b> {data["SENSEX"]["ltp"]}
        <span style='color:#00c853'> ▲ {data["SENSEX"]["change"]}</span>
    </span>

    <span style='margin-right:22px; font-size:13px; color:#bbb'>
        <b style='color:white'>VIX</b> {data["VIX"]["ltp"]}
        <span style='color:#ff1744'> ▼ {data["VIX"]["change"]}</span>
    </span>

    <span style='margin-right:22px; font-size:13px; color:#bbb'>
        <b style='color:white'>DOW</b> {data["DOW"]["ltp"]}
        <span style='color:#00c853'> ▲ {data["DOW"]["change"]}</span>
    </span>

    <span style='margin-right:22px; font-size:13px; color:#bbb'>
        <b style='color:white'>NASDAQ</b> {data["NASDAQ"]["ltp"]}
        <span style='color:#ff1744'> ▼ {data["NASDAQ"]["change"]}</span>
    </span>

    <span style='margin-right:22px; font-size:13px; color:#bbb'>
        <b style='color:white'>GIFT</b> {data["GIFT"]["ltp"]}
        <span style='color:#00c853'> ▲ {data["GIFT"]["change"]}</span>
    </span>

    <span style='margin-right:22px; font-size:13px; color:#bbb'>
        <b style='color:white'>CRUDE</b> {data["CRUDE"]["ltp"]}
        <span style='color:#00c853'> ▲ {data["CRUDE"]["change"]}</span>
    </span>

    <span style='margin-right:22px; font-size:13px; color:#bbb'>
        <b style='color:white'>GOLD</b> {data["GOLD"]["ltp"]}
        <span style='color:#00c853'> ▲ {data["GOLD"]["change"]}</span>
    </span>

    <span style='margin-right:22px; font-size:13px; color:#bbb'>
        <b style='color:white'>SILVER</b> {data["SILVER"]["ltp"]}
        <span style='color:#00c853'> ▲ {data["SILVER"]["change"]}</span>
    </span>

    <span style='margin-right:22px; font-size:13px; color:#bbb'>
        <b style='color:white'>USDINR</b> {data["USDINR"]["ltp"]}
        <span style='color:#00c853'> ▲ {data["USDINR"]["change"]}</span>
    </span>

    <span style='margin-right:22px; font-size:13px; color:#bbb'>
        <b style='color:white'>DXY</b> {data["DXY"]["ltp"]}
        <span style='color:#ff1744'> ▼ {data["DXY"]["change"]}</span>
    </span>

    </div>
    """

    st.markdown(html, unsafe_allow_html=True)
