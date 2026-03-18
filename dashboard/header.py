import streamlit as st

def show_header(data):

    line1 = f"""
    NIFTY {data['nifty']['ltp']} ▲ {data['nifty']['change']} |
    BANKNIFTY {data['banknifty']['ltp']} ▲ {data['banknifty']['change']} |
    SENSEX {data['sensex']['ltp']} ▲ {data['sensex']['change']} |
    VIX {data['vix']['ltp']} ▼ {data['vix']['change']}
    """

    line2 = f"""
    DOW {data['dow']['ltp']} ▲ {data['dow']['change']} |
    NASDAQ {data['nasdaq']['ltp']} ▼ {data['nasdaq']['change']} |
    GIFT {data['gift']['ltp']} ▲ {data['gift']['change']} |
    CRUDE {data['crude']['ltp']} ▲ {data['crude']['change']} |
    GOLD {data['gold']['ltp']} ▲ {data['gold']['change']} |
    SILVER {data['silver']['ltp']} ▲ {data['silver']['change']} |
    USDINR {data['usd']['ltp']} ▲ {data['usd']['change']} |
    DXY {data['dxy']['ltp']} ▼ {data['dxy']['change']}
    """

    st.info(line1)
    st.info(line2)


def check_alerts(data):
    alerts = []

    if abs(data["nifty"]["change"]) > 100:
        alerts.append("⚠️ NIFTY high movement")

    if abs(data["banknifty"]["change"]) > 200:
        alerts.append("⚠️ BANKNIFTY high movement")

    return alerts
