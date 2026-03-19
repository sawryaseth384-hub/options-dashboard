import streamlit as st

def show_header(data):

    if not data:
        st.warning("No Data")
        return

    def format_item(d):
        name = d.get("name", "")
        price = d.get("price", 0)
        change = float(d.get("change", 0))

        color = "#00c853" if change >= 0 else "#ff1744"
        arrow = "▲" if change >= 0 else "▼"

        return f"""
        <div class="item">
            <span class="name">{name}</span>
            <span class="price">{price}</span>
            <span class="change" style="color:{color}">
                {arrow} {change}
            </span>
        </div>
        """

    html = "".join([format_item(d) for d in data])

    st.markdown(f"""
    <style>

    .header-box {{
        background: #0b1220;
        padding: 10px 15px;
        border-radius: 12px;
        overflow-x: auto;
        white-space: nowrap;
    }}

    .item {{
        display: inline-block;
        margin-right: 25px;
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

    .change {{
        font-weight: 500;
    }}

    </style>

    <div class="header-box">
        {html}
    </div>
    """, unsafe_allow_html=True)
