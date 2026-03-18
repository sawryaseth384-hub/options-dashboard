import streamlit as st

def show_header(data):

    def item(name, ltp, chg):
        color = "#00c853" if chg >= 0 else "#ff1744"
        arrow = "▲" if chg >= 0 else "▼"

        return f"<span style='margin-right:18px; font-size:13px; color:#bbb'><b style='color:white'>{name}</b> {ltp} <span style='color:{color}'> {arrow} {chg}</span></span>"

    line1 = (
        item("NIFTY", data["NIFTY"]["ltp"], data["NIFTY"]["change"]) +
        item("BANKNIFTY", data["BANKNIFTY"]["ltp"], data["BANKNIFTY"]["change"]) +
        item("SENSEX", data["SENSEX"]["ltp"], data["SENSEX"]["change"]) +
        item("VIX", data["VIX"]["ltp"], data["VIX"]["change"]) +
        item("DOW", data["DOW"]["ltp"], data["DOW"]["change"]) +
        item("NASDAQ", data["NASDAQ"]["ltp"], data["NASDAQ"]["change"]) +
        item("GIFT", data["GIFT"]["ltp"], data["GIFT"]["change"])
    )

    line2 = (
        item("CRUDE", data["CRUDE"]["ltp"], data["CRUDE"]["change"]) +
        item("GOLD", data["GOLD"]["ltp"], data["GOLD"]["change"]) +
        item("SILVER", data["SILVER"]["ltp"], data["SILVER"]["change"]) +
        item("USDINR", data["USDINR"]["ltp"], data["USDINR"]["change"]) +
        item("DXY", data["DXY"]["ltp"], data["DXY"]["change"])
    )

    html = f"""
    <div style='background:#0b1220; padding:10px; border-radius:10px;'>
        <marquee>{line1}</marquee>
        <marquee>{line2}</marquee>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def check_alerts(data):

    alerts = []

    if abs(data["NIFTY"]["change"]) > 100:
        alerts.append("⚡ NIFTY High Movement")

    if abs(data["BANKNIFTY"]["change"]) > 250:
        alerts.append("⚡ BANKNIFTY Volatility")

    if abs(data["VIX"]["change"]) > 1:
        alerts.append("⚠️ VIX Spike")

    return alerts
