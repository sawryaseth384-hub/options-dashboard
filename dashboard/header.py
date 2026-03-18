import streamlit as st

def show_header(data):

    def item(name, ltp, chg):
        color = "#00c853" if chg >= 0 else "#ff1744"
        arrow = "▲" if chg >= 0 else "▼"

        return f"""
        <span style='margin-right:22px; font-size:13px; color:#bbb'>
            <b style='color:white'>{name}</b> {ltp}
            <span style='color:{color}'> {arrow} {chg}</span>
        </span>
        """

    html = f"""
    <div style='
        background:#0b1220;
        padding:10px 20px;
        border-radius:10px;
        margin-bottom:15px;
        overflow-x:auto;
        white-space:nowrap;
    '>

    {item("NIFTY", data["NIFTY"]["ltp"], data["NIFTY"]["change"])}
    {item("BANKNIFTY", data["BANKNIFTY"]["ltp"], data["BANKNIFTY"]["change"])}
    {item("SENSEX", data["SENSEX"]["ltp"], data["SENSEX"]["change"])}
    {item("VIX", data["VIX"]["ltp"], data["VIX"]["change"])}

    {item("DOW", data["DOW"]["ltp"], data["DOW"]["change"])}
    {item("NASDAQ", data["NASDAQ"]["ltp"], data["NASDAQ"]["change"])}
    {item("GIFT", data["GIFT"]["ltp"], data["GIFT"]["change"])}

    {item("CRUDE", data["CRUDE"]["ltp"], data["CRUDE"]["change"])}
    {item("GOLD", data["GOLD"]["ltp"], data["GOLD"]["change"])}
    {item("SILVER", data["SILVER"]["ltp"], data["SILVER"]["change"])}

    {item("USDINR", data["USDINR"]["ltp"], data["USDINR"]["change"])}
    {item("DXY", data["DXY"]["ltp"], data["DXY"]["change"])}

    </div>
    """

    st.markdown(html, unsafe_allow_html=True)
