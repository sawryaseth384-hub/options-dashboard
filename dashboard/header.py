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
            price = d.get("price", 0)
            change = float(d.get("change", 0))

            color = "#00c853" if change >= 0 else "#ff1744"
            arrow = "▲" if change >= 0 else "▼"

            html += f"""
            <div class="item">
                <span class="name">{name}</span>
                <span class="price">{price}</span>
                <span class="change" style="color:{color}">
                    {arrow} {change}
                </span>
            </div>
            """
        return html

    row1_html = build_row(row1)
    row2_html = build_row(row2)

    html = f"""
    <style>
    body {{
        margin:0;
    }}

    .box {{
        background:#0b1220;
        padding:12px 15px;
        border-radius:12px;
        font-family: Arial;
    }}

    .row {{
        display:grid;
        grid-template-columns: repeat(6, auto);
        gap:20px;
        margin-bottom:6px;
    }}

    .item {{
        color:#bbb;
        font-size:13px;
        white-space:nowrap;
    }}

    .name {{
        color:white;
        font-weight:600;
        margin-right:6px;
    }}

    .price {{
        margin-right:6px;
    }}

    .change {{
        font-weight:500;
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

    components.html(html, height=110)
