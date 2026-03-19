import streamlit as st

def show_header(data):

    idx = data["indices"]
    glb = data["global"]
    cmd = data["commodities"]
    cur = data["currency"]

    def item(name, value, change):
        try:
            change = float(change)
        except:
            change = 0

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

    st.markdown(f"""
    <div style="background:#0f172a; padding:6px 10px; border-radius:8px; font-size:13px; overflow:hidden;">

        <div style="white-space:nowrap; display:inline-block; animation: scroll1 20s linear infinite;">
            {line1} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {line1}
        </div>

        <div style="white-space:nowrap; display:inline-block; animation: scroll2 25s linear infinite;">
            {line2} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {line2}
        </div>

    </div>

    <style>
    @keyframes scroll1 {{
        0% {{ transform: translateX(100%); }}
        100% {{ transform: translateX(-100%); }}
    }}

    @keyframes scroll2 {{
        0% {{ transform: translateX(100%); }}
        100% {{ transform: translateX(-100%); }}
    }}
    </style>
    """, unsafe_allow_html=True)
