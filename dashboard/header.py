import streamlit as st

def show_header(data):

    def item(d):
        try:
            change = float(d.get("change", 0))
        except:
            change = 0

        value = d.get("ltp", "-")
        name = d.get("name", "-")

        color = "#00c853" if change >= 0 else "#ff1744"
        arrow = "▲" if change >= 0 else "▼"

        return f"<b>{name}</b> {value} <span style='color:{color}'> {arrow} {change}</span>"

    # 🔥 SAFE LOOP
    try:
        line = " | ".join([item(d) for d in data])
    except:
        line = "No Data"

    html = f"""
    <div style="background:#0f172a; padding:8px; border-radius:8px; overflow:hidden; color:white;">
        <marquee scrollamount="5">
            {line}
        </marquee>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)
