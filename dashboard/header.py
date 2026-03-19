import streamlit as st

def show_header(data):

    # ❌ अगर data empty है
    if not data:
        st.warning("No Data")
        return

    html = ""

    # 🔥 Loop through data
    for d in data:
        name = d.get("name", "")
        price = d.get("price", 0)
        change = float(d.get("change", 0))

        color = "#00c853" if change >= 0 else "#ff1744"
        arrow = "▲" if change >= 0 else "▼"

        html += f"""
        <span style='margin-right:22px; font-size:13px; color:#bbb'>
            <b style='color:white'>{name}</b> {price}
            <span style='color:{color}'> {arrow} {change}</span>
        </span>
        """

    # 🔥 Final render
    st.markdown(f"""
    <div style="background:#0b1220; padding:8px; border-radius:10px; overflow-x:auto; white-space:nowrap;">
        {html}
    </div>
    """, unsafe_allow_html=True)
