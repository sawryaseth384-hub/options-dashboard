import streamlit as st
import streamlit.components.v1 as components

def show_header(data):

    if not data:
        st.warning("No Data")
        return

    row1 = data[:4]   # Indian
    row2 = data[4:]   # Global + Commodity

    def build_row(row):
        html = ""
        for d in row:
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
        return html

    row1_html = build_row(row1)
    row2_html = build_row(row2)

    final_html = f"""
    <style>
    .box {{
        background:#0b1220;
        padding:10px 15px;
        border-radius:10px;
        font-size:13px;
    }}

    .row {{
        display:flex;
        flex-wrap:wrap;
        gap:20px;
        margin-bottom:5px;
    }}

    .item {{
        color:#bbb;
    }}

    b {{
        color:white;
        margin-right:5px;
    }}
    </style>

    <div class="box">
        <div class="row">
            {row1_html}
        </div>
        <div class="row">
            {row2_html}
        </div>
    </div>
    """

    components.html(final_html, height=110, scrolling=False))
