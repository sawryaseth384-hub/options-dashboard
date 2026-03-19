import streamlit as st

def show_header(data):

    if not data:
        st.warning("No Data")
        return

    html = ""

    for d in data:
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

    st.markdown(f"""
    <style>

    .header-box {{
        background: #0b1220;
        padding: 10px;
        border-radius: 10px;
        overflow-x: auto;
        white-space: nowrap;
    }}

    .item {{
        display: inline-block;
        margin-right: 20px;
        font-size: 13px;
    }}

    .name {{
        color: #aaa;
        margin-right: 5px;
    }}

    .price {{
        color: white;
        font-weight: 600;
        margin-right: 5px;
    }}

    </style>

    <div class="header-box">
        {html}
    </div>
    """, unsafe_allow_html=True)
