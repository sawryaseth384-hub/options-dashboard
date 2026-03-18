import streamlit as st


def item(name, ltp, change):
    color = "#00c853" if change >= 0 else "#ff1744"
    arrow = "▲" if change >= 0 else "▼"

    return f"{name} {ltp} {arrow} {change}"


def show_header(data):

    line1 = " | ".join([
        item("NIFTY", data["nifty"]["ltp"], data["nifty"]["change"]),
        item("BANKNIFTY", data["banknifty"]["ltp"], data["banknifty"]["change"]),
        item("SENSEX", data["sensex"]["ltp"], data["sensex"]["change"]),
        item("VIX", data["vix"]["ltp"], data["vix"]["change"]),
    ])

    line2 = " | ".join([
        item("DOW", data["dow"]["ltp"], data["dow"]["change"]),
        item("NASDAQ", data["nasdaq"]["ltp"], data["nasdaq"]["change"]),
        item("GIFT", data["gift"]["ltp"], data["gift"]["change"]),
        item("CRUDE", data["crude"]["ltp"], data["crude"]["change"]),
        item("GOLD", data["gold"]["ltp"], data["gold"]["change"]),
        item("SILVER", data["silver"]["ltp"], data["silver"]["change"]),
        item("USDINR", data["usd"]["ltp"], data["usd"]["change"]),
        item("DXY", data["dxy"]["ltp"], data["dxy"]["change"]),
    ])

    st.markdown("### 📊 Market Live")
    st.info(line1)
    st.info(line2)


def check_alerts(data):
    alerts = []

    if abs(data["nifty"]["change"]) > 100:
        alerts.append("⚠️ NIFTY high movement")

    if abs(data["banknifty"]["change"]) > 200:
        alerts.append("⚠️ BANKNIFTY high movement")

    if abs(data["vix"]["change"]) > 1:
        alerts.append("⚠️ VIX spike")

    return alerts
