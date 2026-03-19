import streamlit as st

def show_header(data):

    def item(d):
        change = float(d["change"])
        color = "#00c853" if change >= 0 else "#ff1744"
        arrow = "▲" if change >= 0 else "▼"

        return f"<b>{d['name']}</b> {d['ltp']} <span style='color:{color}'> {arrow} {change}</span>"

    line = " | ".join([item(d) for d in data])

    html = f"""
    <div style="background:#0f172a; padding:8px; border-radius:8px; overflow:hidden; color:white;">
        <marquee scrollamount="5">
            {line}
        </marquee>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)
