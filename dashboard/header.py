import streamlit as st

def show_header(data):

    idx = data["indices"]
    glb = data["global"]
    cmd = data["commodities"]
    cur = data["currency"]

    def item(name, value, change):
        color = "#00c853" if change >= 0 else "#ff1744"
        arrow = "▲" if change >= 0 else "▼"
        return f"<b style='color:white'>{name}</b> {value} <span style='color:{color}'> {arrow} {change}</span>"

    line1 = " | ".join([
        item("NIFTY", idx["nifty"]["ltp"], idx["nifty"]["change"]),
        item("BANKNIFTY", idx["banknifty"]["ltp"], idx["banknifty"]["change"]),
        item("SENSEX", idx["sensex"]["ltp"], idx["sensex"]["change"]),
        item("VIX", idx["vix"]["ltp"], idx["vix"]["change"]),
    ])

    line2 = " | ".join([
        item("DOW", glb["dow"]["ltp"], glb["dow"]["change"]),
        item("NASDAQ", glb["nasdaq"]["ltp"], glb["nasdaq"]["change"]),
        item("GIFT", glb["gift"]["ltp"], glb["gift"]["change"]),
        item("CRUDE", cmd["crude"]["ltp"], cmd["crude"]["change"]),
        item("GOLD", cmd["gold"]["ltp"], cmd["gold"]["change"]),
        item("SILVER", cmd["silver"]["ltp"], cmd["silver"]["change"]),
        item("USDINR", cur["usd"]["ltp"], cur["usd"]["change"]),
        item("DXY", cur["dxy"]["ltp"], cur["dxy"]["change"]),
    ])

    # 🔥 Slim UI
    st.markdown(f"""
    <div style="background:#0f172a; padding:6px 10px; border-radius:6px; font-size:13px;">
        <marquee behavior="scroll" direction="left">{line1}</marquee>
        <marquee behavior="scroll" direction="left">{line2}</marquee>
    </div>
    """, unsafe_allow_html=True)
