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

    # 🔥 LINE 1 (Indian Market)
    line1 = (
        item("NIFTY", data["nifty"]["ltp"], data["nifty"]["change"]) +
        item("BANKNIFTY", data["banknifty"]["ltp"], data["banknifty"]["change"]) +
        item("SENSEX", data["sensex"]["ltp"], data["sensex"]["change"]) +
        item("VIX", data["vix"]["ltp"], data["vix"]["change"])
    )

    # 🔥 LINE 2 (Global + Commodity)
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

    # 🔥 STYLE (Dhan जैसा top strip)
    st.markdown("""
        <style>
        .header-strip {
            background-color: #0E1117;
            padding: 8px 15px;
            border-radius: 8px;
            margin-bottom: 5px;
            overflow-x: auto;
            white-space: nowrap;
        }
        </style>
    """, unsafe_allow_html=True)

    # 🔥 OUTPUT
    st.markdown(f"<div class='header-strip'>{line1}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='header-strip'>{line2}</div>", unsafe_allow_html=True)
