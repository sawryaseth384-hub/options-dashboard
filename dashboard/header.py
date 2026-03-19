import streamlit as st

def show_header(data):

    if not data:
        st.warning("No Data")
        return

    # 🔥 HTML build
    html = ""

    for d in data:
        name = d.get("name", "")
        price = d.get("price") or d.get("ltp") or 0
        change = float(d.get("change", 0))

        color = "#00c853" if change >= 0 else "#ff1744"
        arrow = "▲" if change >= 0 else "▼"

        html += f"""
        <span style="margin-right:20px; font-size:13px;">
            <b style="color:white;">{name}</b> {price}
            <span style="color:{color};"> {arrow} {change}</span>
        </span>
        """

    # 🔥 IMPORTANT FIX (div wrap + no extra spacing)
    final_html = f"""
    <div style="
        background:#0b1220;
        padding:10px;
        border-radius:10px;
        overflow-x:auto;
        white-space:nowrap;
    ">
        {html}
    </div>
    """

    # 🔥 MUST: unsafe_allow_html=True
    st.markdown(final_html, unsafe_allow_html=True)
