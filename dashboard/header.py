import streamlit as st
import streamlit.components.v1 as components

def show_header(data):

    if not data:
        st.warning("No Data")
        return

    html = ""

    for d in data:
        name = d.get("name", "")
        price = d.get("price") or d.get("ltp") or 0
        change = float(d.get("change", 0))

        color = "#00c853" if change >= 0 else "#ff1744"
        arrow = "▲" if change >= 0 else "▼"

        html += f"""
        <span class="item">
            <b>{name}</b> {price}
            <span style="color:{color}"> {arrow} {change}</span>
        </span>
        """

    final_html = f"""
    <div style="
        background:#0b1220;
        padding:10px;
        border-radius:10px;
        overflow-x:auto;
        white-space:nowrap;
        font-size:13px;
        color:#bbb;
    ">
        {html}
    </div>
    """

    # 🔥 THIS FIXES EVERYTHING
    components.html(final_html, height=60)
