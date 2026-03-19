import streamlit as st
import streamlit.components.v1 as components

def show_header(data):

    if not data:
        st.warning("No Data")
        return

    items_html = ""

    for d in data:
        name = d.get("name", "")
        price = d.get("price") or d.get("ltp") or 0
        change = float(d.get("change", 0))

        color = "#00c853" if change >= 0 else "#ff1744"
        arrow = "▲" if change >= 0 else "▼"

        items_html += f"""
        <span class="item">
            <b>{name}</b> {price}
            <span style="color:{color}"> {arrow} {change}</span>
        </span>
        """

    final_html = f"""
    <style>
    .ticker-container {{
        background:#0b1220;
        padding:10px;
        border-radius:10px;
        overflow:hidden;
        white-space:nowrap;
    }}

    .ticker {{
        display:inline-block;
        animation: scroll 25s linear infinite;
    }}

    .item {{
        margin-right:25px;
        font-size:13px;
        color:#bbb;
    }}

    @keyframes scroll {{
        0% {{ transform: translateX(100%); }}
        100% {{ transform: translateX(-100%); }}
    }}
    </style>

    <div class="ticker-container">
        <div class="ticker">
            {items_html}
            {items_html}  <!-- duplicate for smooth loop -->
        </div>
    </div>
    """

    components.html(final_html, height=60)
