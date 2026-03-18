import streamlit as st


# 🔥 SINGLE ITEM DESIGN
def item(name, ltp, change):
    color = "#00c853" if change >= 0 else "#ff1744"
    arrow = "▲" if change >= 0 else "▼"

    return f"""
    <span style='margin-right:20px; font-size:13px; color:#bbb'>
        <b style='color:white'>{name}</b> {ltp}
        <span style='color:{color}'> {arrow} {change}</span>
    </span>
    """


# 🔥 HEADER MAIN
def show_header(data):

    line1 = (
        item("NIFTY", data["nifty"]["ltp"], data["nifty"]["change"]) +
        item("BANKNIFTY", data["banknifty"]["ltp"], data["banknifty"]["change"]) +
        item("SENSEX", data["sensex"]["ltp"], data["sensex"]["change"]) +
        item("VIX", data["vix"]["ltp"], data["vix"]["change"])
    )

    line2 = (
        item("DOW", data["dow"]["ltp"], data["dow"]["change"]) +
        item("NASDAQ", data["nasdaq"]["ltp"], data["nasdaq"]["change"]) +
        item("GIFT", data["gift"]["ltp"], data["gift"]["change"]) +
        item("CRUDE", data["crude"]["ltp"], data["crude"]["change"]) +
        item("GOLD", data["gold"]["ltp"], data["gold"]["change"]) +
        item("SILVER", data["silver"]["ltp"], data["silver"]["change"]) +
        item("USDINR", data["usd"]["ltp"], data["usd"]["change"]) +
        item("DXY", data["dxy"]["ltp"], data["dxy"]["change"])
    )

    st.markdown(f"""
    <div style="
        background: linear-gradient(90deg,#0f172a,#020617);
        padding:10px 15px;
        border-radius:10px;
        margin-bottom:10px;
        overflow:hidden;
    ">

        <marquee behavior="scroll" direction="left">
            {line1}
        </marquee>

        <marquee behavior="scroll" direction="left">
            {line2}
        </marquee>

    </div>
    """, unsafe_allow_html=True)


# 🔥 ALERT SYSTEM
def check_alerts(data):
    alerts = []

    if abs(data["nifty"]["change"]) > 100:
        alerts.append("⚠️ NIFTY high movement")

    if abs(data["banknifty"]["change"]) > 200:
        alerts.append("⚠️ BANKNIFTY volatility high")

    if abs(data["vix"]["change"]) > 1:
        alerts.append("⚠️ VIX spike detected")

    return alerts
