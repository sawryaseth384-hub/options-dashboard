import streamlit as st

def show_header(data):

    html = f"""
    <span style='margin-right:20px; font-size:13px; color:#ccc'>
        <b style='color:white'>NIFTY</b> {data["NIFTY"]["ltp"]}
        <span style='color:#00c853'> ▲ {data["NIFTY"]["change"]}</span>
    </span>

    <span style='margin-right:20px; font-size:13px; color:#ccc'>
        <b style='color:white'>BANKNIFTY</b> {data["BANKNIFTY"]["ltp"]}
        <span style='color:#00c853'> ▲ {data["BANKNIFTY"]["change"]}</span>
    </span>

    <span style='margin-right:20px; font-size:13px; color:#ccc'>
        <b style='color:white'>SENSEX</b> {data["SENSEX"]["ltp"]}
        <span style='color:#00c853'> ▲ {data["SENSEX"]["change"]}</span>
    </span>

    <span style='margin-right:20px; font-size:13px; color:#ccc'>
        <b style='color:white'>VIX</b> {data["VIX"]["ltp"]}
        <span style='color:#ff1744'> ▼ {data["VIX"]["change"]}</span>
    </span>
    """

    st.markdown(html, unsafe_allow_html=True)
