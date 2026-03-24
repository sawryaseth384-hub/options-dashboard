import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

def render_header(nifty_spot=None, banknifty_spot=None):
    """Top bar with NIFTY & BANKNIFTY spot prices."""
    col1, col2 = st.columns(2)
    col1.metric("🇮🇳 NIFTY", f"{nifty_spot:,.2f}" if nifty_spot else "N/A")
    col2.metric("🏦 BANKNIFTY", f"{banknifty_spot:,.2f}" if banknifty_spot else "N/A")
    st.markdown("---")

def render_decision_bar(spot, pcr, atm_strike, best_ce, final_signal, call_trap, put_trap):
    """Level 1 – Decision Bar (always visible at top)."""
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.metric("📍 Spot", f"{spot:.2f}")
    col2.metric("📊 PCR", f"{pcr:.2f}")
    col3.metric("🧠 Bias", "Bullish" if pcr > 1 else ("Bearish" if pcr < 0.7 else "Neutral"))
    col4.metric("🎯 ATM", f"{atm_strike}")
    col5.metric("🔥 Best", f"{best_ce} CE")
    col6.metric("🚀 Signal", final_signal)
    col7.metric("⚠️ Trap", "Call Trap" if call_trap else ("Put Trap" if put_trap else "No"))
    st.markdown("---")

def render_core_analysis(support, resistance, max_pain, atm_pcr, pcr):
    """Level 2 – Core Analysis summary."""
    st.subheader("📌 Core Analysis")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.success(f"🟢 Support: {support[0] if support else 'N/A'}")
    c2.error(f"🔴 Resistance: {resistance[0] if resistance else 'N/A'}")
    c3.info(f"🎯 Max Pain: {max_pain}")
    c4.info(f"📊 ATM PCR: {atm_pcr:.2f}" if atm_pcr else "N/A")
    c5.info(f"🔥 OI Strength: {'High' if pcr > 1.2 or pcr < 0.8 else 'Moderate'}")

def render_option_chain_table(df):
    """Level 3 – Scrollable option chain with all advanced columns."""
    st.subheader("📋 Option Chain + Advanced OI")
    display_cols = [
        "Strike", "CE OI", "PE OI", "CE OI Change", "PE OI Change",
        "CE LTP", "PE LTP", "CE Delta", "PE Delta",
        "CE BuildUp", "PE BuildUp", "Signal",
        "CE OI Velocity", "PE OI Velocity",
        "CE OI Divergence", "PE OI Divergence",
        "CE OI Shift", "PE OI Shift",
        "CE Action", "PE Action", "Writers vs Buyers"
    ]
    available = [c for c in display_cols if c in df.columns]
    st.dataframe(df[available].style.format({
        "CE OI": "{:,.0f}", "PE OI": "{:,.0f}",
        "CE OI Change": "{:,.0f}", "PE OI Change": "{:,.0f}",
        "CE LTP": "{:.2f}", "PE LTP": "{:.2f}",
        "CE Delta": "{:.3f}", "PE Delta": "{:.3f}",
        "CE OI Velocity": "{:,.0f}", "PE OI Velocity": "{:,.0f}",
    }), height=500, use_container_width=True)

def render_charts(df, support, resistance, spot):
    """Level 4 – OI bar chart and LTP line chart."""
    st.subheader("📈 Charts")
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        fig_oi = px.bar(df, x="Strike", y=["CE OI", "PE OI"], barmode="group", title="OI & Volume")
        for s in support[:2]:
            fig_oi.add_vline(x=s, line_dash="dash", line_color="green")
        for r in resistance[:2]:
            fig_oi.add_vline(x=r, line_dash="dash", line_color="red")
        fig_oi.add_vline(x=spot, line_dash="dot", line_color="yellow")
        st.plotly_chart(fig_oi, use_container_width=True)
    with chart_col2:
        ltp_df = df.melt(id_vars="Strike", value_vars=["CE LTP", "PE LTP"], var_name="Option", value_name="LTP")
        fig_ltp = px.line(ltp_df, x="Strike", y="LTP", color="Option", title="CE LTP vs PE LTP", markers=True)
        fig_ltp.add_vline(x=spot, line_dash="dot", line_color="yellow")
        st.plotly_chart(fig_ltp, use_container_width=True)

def render_candlestick(sec_id, segment):
    """Level 4 – Candlestick chart (uses chart.py)."""
    st.subheader("🕯️ Candlestick (Spot)")
    from dhan_data.chart import get_candle_data, plot_candle
    try:
        df_candle = get_candle_data(sec_id, segment)
        if df_candle is not None:
            fig_candle, trend = plot_candle(df_candle)
            st.write(f"Trend: {trend}")
            st.plotly_chart(fig_candle, use_container_width=True)
        else:
            st.warning("Candlestick data not available.")
    except Exception as e:
        st.warning(f"Candlestick error: {e}")

def render_strike_analysis(df, sec_id):
    """Level 5 – Strike analysis with detailed metrics and OI velocity graph."""
    st.subheader("🔍 Strike Analysis")
    selected_strike = st.selectbox("Select Strike", df["Strike"].tolist())
    if selected_strike:
        row = df[df["Strike"] == selected_strike].iloc[0]
        col_a, col_b = st.columns(2)
        with col_a:
            st.write(f"**CE OI**: {row['CE OI']:,.0f}")
            st.write(f"**CE LTP**: {row['CE LTP']:.2f}")
            st.write(f"**CE Delta**: {row['CE Delta']:.3f}")
            st.write(f"**CE BuildUp**: {row['CE BuildUp']}")
            st.write(f"**CE Action**: {row['CE Action']}")
        with col_b:
            st.write(f"**PE OI**: {row['PE OI']:,.0f}")
            st.write(f"**PE LTP**: {row['PE LTP']:.2f}")
            st.write(f"**PE Delta**: {row['PE Delta']:.3f}")
            st.write(f"**PE BuildUp**: {row['PE BuildUp']}")
            st.write(f"**PE Action**: {row['PE Action']}")

        st.write("**OI Velocity Graph** (last 5 intervals)")
        # Placeholder – you can replace with actual historical OI fetch
        history_ce = [1000, 1200, 1400, 1600, 1800]
        history_pe = [800, 950, 1100, 1250, 1400]
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Scatter(y=history_ce, name="CE OI", mode="lines+markers"))
        fig_hist.add_trace(go.Scatter(y=history_pe, name="PE OI", mode="lines+markers"))
        fig_hist.update_layout(title="OI History (Mock)", height=300)
        st.plotly_chart(fig_hist, use_container_width=True)

def render_pro_insights(net_delta):
    """Level 6 – Pro insights (FII/DII, IV, Gamma, Delta Exposure)."""
    st.subheader("🚀 Pro Insights")
    pro1, pro2, pro3, pro4 = st.columns(4)
    pro1.metric("FII Net Position (cr)", "1,240")   # placeholder
    pro2.metric("DII Net Position (cr)", "-320")
    pro3.metric("IV (ATM)", "14.8%")
    pro4.metric("Gamma Exposure", "₹4.2 Lakh / pt")
    st.write(f"**Delta Exposure:** {net_delta:,.0f}")
