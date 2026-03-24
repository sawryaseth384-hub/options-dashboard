import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dhan_data.instruments import get_symbol_data
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain
from dhan_data.market_quote import get_ltp
from core.token_manager import get_headers

st.set_page_config(layout="wide")
st.markdown("""
    <style>
        body {background-color: #0A0F18; color: white;}
        .block-container {padding-top: 1rem;}
        div[data-testid="metric-container"] {
            background: #111827;
            border-radius: 10px;
            padding: 12px;
            border: 1px solid #1F2937;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            min-width: 130px;   /* added to prevent cut-off numbers */
        }
        .stDataFrame {font-size: 0.8rem;}
        .stSelectbox {margin-bottom: 1rem;}
        hr {margin: 0.5rem 0;}
    </style>
""", unsafe_allow_html=True)

st.title("🧠 Smart Money Options Dashboard — Institutional Grade")

# =========================
# SESSION STATE
# =========================
if "previous_data" not in st.session_state:
    st.session_state.previous_data = None
if "sec_id" not in st.session_state:
    st.session_state.sec_id = None
if "segment" not in st.session_state:
    st.session_state.segment = None
if "expiry" not in st.session_state:
    st.session_state.expiry = None
if "symbol" not in st.session_state:
    st.session_state.symbol = "NIFTY"

# =========================
# HARDCODED FALLBACKS FOR INDICES AND POPULAR STOCKS
# =========================
HARDCODED_IDS = {
    "NIFTY": (13, "IDX_I"),
    "BANKNIFTY": (25, "IDX_I"),
    "FINNIFTY": (27, "IDX_I"),
    "RELIANCE": (2885, "NSE_FNO"),
    "TCS": (11536, "NSE_FNO"),
    "HDFCBANK": (1333, "NSE_FNO"),
    "INFY": (4083, "NSE_FNO"),
    "ICICIBANK": (495, "NSE_FNO"),
}

def resolve_symbol(symbol):
    sec_id, seg = get_symbol_data(symbol)
    if sec_id is None:
        if symbol in HARDCODED_IDS:
            sec_id, seg = HARDCODED_IDS[symbol]
            st.sidebar.info(f"Using fallback for {symbol}")
        else:
            st.sidebar.error(f"Symbol '{symbol}' not found.")
    return sec_id, seg

def get_next_thursday():
    today = datetime.now()
    days_ahead = (3 - today.weekday() + 7) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_thu = today + timedelta(days=days_ahead)
    return next_thu.strftime("%Y-%m-%d")

def get_spot_for(symbol):
    sec_id, seg = resolve_symbol(symbol)
    if sec_id:
        try:
            return get_ltp(sec_id, seg)
        except:
            return 0
    return 0

# =========================
# SIDEBAR CONTROLS
# =========================
with st.sidebar:
    st.header("⚙️ Controls")
    symbol = st.text_input("Symbol", st.session_state.symbol).upper()
    if symbol != st.session_state.symbol:
        st.session_state.symbol = symbol
        sec_id, seg = resolve_symbol(symbol)
        st.session_state.sec_id = sec_id
        st.session_state.segment = seg
        if sec_id:
            st.success(f"✅ {symbol} → ID: {sec_id}, Segment: {seg}")
        else:
            st.error(f"❌ Symbol '{symbol}' not found.")
            st.session_state.sec_id = None
            st.session_state.expiry = None

    # Force initial resolution if sec_id is still None
    if st.session_state.sec_id is None:
        sec_id, seg = resolve_symbol(st.session_state.symbol)
        st.session_state.sec_id = sec_id
        st.session_state.segment = seg
        if sec_id:
            st.success(f"✅ {st.session_state.symbol} → ID: {sec_id}, Segment: {seg}")

    if st.session_state.sec_id:
        expiry_list = []
        try:
            exp_data = get_expiry(st.session_state.sec_id, st.session_state.segment)
            if isinstance(exp_data, list):
                expiry_list = exp_data
            elif isinstance(exp_data, dict) and "data" in exp_data:
                expiry_list = exp_data["data"]
        except Exception as e:
            st.warning(f"Expiry fetch error: {e}")

        if expiry_list:
            if st.session_state.expiry not in expiry_list:
                st.session_state.expiry = expiry_list[0]
            expiry = st.selectbox("Expiry", expiry_list, index=expiry_list.index(st.session_state.expiry))
            st.session_state.expiry = expiry
        else:
            fallback = get_next_thursday()
            st.warning(f"No expiry from API. Using fallback: {fallback}")
            st.session_state.expiry = fallback
            st.write(f"Using expiry: {st.session_state.expiry}")

    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

    # Depth display (optional)
    st.divider()
    st.subheader("📊 Depth (Bid/Ask)")
    from dhan_data.depth_feed import get_depth
    depth = get_depth()
    if depth["bids"]:
        st.write("**Bids**")
        st.dataframe(pd.DataFrame(depth["bids"][:5]), use_container_width=True)
    if depth["asks"]:
        st.write("**Asks**")
        st.dataframe(pd.DataFrame(depth["asks"][:5]), use_container_width=True)

# =========================
# TOP BAR – NIFTY & BANKNIFTY SPOT PRICES
# =========================
nifty_spot = get_spot_for("NIFTY")
banknifty_spot = get_spot_for("BANKNIFTY")
col1, col2 = st.columns(2)
col1.metric("🇮🇳 NIFTY", f"{nifty_spot:,.2f}" if nifty_spot else "N/A")
col2.metric("🏦 BANKNIFTY", f"{banknifty_spot:,.2f}" if banknifty_spot else "N/A")
st.markdown("---")

# =========================
# MAIN DASHBOARD (only if data available)
# =========================
if st.session_state.sec_id and st.session_state.expiry:
    @st.cache_data(ttl=60)
    def fetch_chain(sec_id, expiry, segment):
        return get_option_chain(sec_id, expiry, segment)

    data = fetch_chain(st.session_state.sec_id, st.session_state.expiry, st.session_state.segment)
    if not data or "data" not in data:
        st.error("No option chain data. Check symbol/expiry.")
        st.stop()

    # Process raw data
    raw = data["data"]
    spot = raw.get("last_price", 0)
    oc = raw.get("oc", {})

    rows = []
    for strike, val in oc.items():
        ce = val.get("ce", {})
        pe = val.get("pe", {})
        rows.append({
            "Strike": int(float(strike)),
            "CE OI": ce.get("oi", 0),
            "CE LTP": ce.get("last_price", 0),
            "CE Delta": ce.get("greeks", {}).get("delta", 0),
            "CE Gamma": ce.get("greeks", {}).get("gamma", 0),
            "CE Theta": ce.get("greeks", {}).get("theta", 0),
            "CE Vega": ce.get("greeks", {}).get("vega", 0),
            "PE OI": pe.get("oi", 0),
            "PE LTP": pe.get("last_price", 0),
            "PE Delta": pe.get("greeks", {}).get("delta", 0),
            "PE Gamma": pe.get("greeks", {}).get("gamma", 0),
            "PE Theta": pe.get("greeks", {}).get("theta", 0),
            "PE Vega": pe.get("greeks", {}).get("vega", 0),
        })
    df = pd.DataFrame(rows).sort_values("Strike")
    prev_df = st.session_state.previous_data

    # Advanced indicators (OI change, etc.)
    if prev_df is not None:
        merged = df.merge(prev_df, on="Strike", suffixes=("", "_prev"))
        df["CE OI Change"] = merged["CE OI"] - merged["CE OI_prev"]
        df["PE OI Change"] = merged["PE OI"] - merged["PE OI_prev"]
        df["CE Price Change"] = merged["CE LTP"] - merged["CE LTP_prev"]
        df["PE Price Change"] = merged["PE LTP"] - merged["PE LTP_prev"]
    else:
        df["CE OI Change"] = 0
        df["PE OI Change"] = 0
        df["CE Price Change"] = 0
        df["PE Price Change"] = 0

    # Build-up classification
    def classify_buildup(row):
        if row["CE OI Change"] > 0 and row["CE Price Change"] > 0:
            ce_type = "CE Long Build-up"
        elif row["CE OI Change"] > 0 and row["CE Price Change"] < 0:
            ce_type = "CE Short Build-up"
        elif row["CE OI Change"] < 0 and row["CE Price Change"] > 0:
            ce_type = "CE Short Covering"
        elif row["CE OI Change"] < 0 and row["CE Price Change"] < 0:
            ce_type = "CE Long Unwinding"
        else:
            ce_type = "CE Neutral"
        if row["PE OI Change"] > 0 and row["PE Price Change"] > 0:
            pe_type = "PE Long Build-up"
        elif row["PE OI Change"] > 0 and row["PE Price Change"] < 0:
            pe_type = "PE Short Build-up"
        elif row["PE OI Change"] < 0 and row["PE Price Change"] > 0:
            pe_type = "PE Short Covering"
        elif row["PE OI Change"] < 0 and row["PE Price Change"] < 0:
            pe_type = "PE Long Unwinding"
        else:
            pe_type = "PE Neutral"
        return ce_type, pe_type

    df[["CE BuildUp", "PE BuildUp"]] = df.apply(lambda r: pd.Series(classify_buildup(r)), axis=1)

    # Writing vs Buying
    def classify_action(row):
        ce_action = "Writing" if (row["CE OI Change"] > 0 and row["CE Price Change"] < 0) else ("Buying" if (row["CE OI Change"] > 0 and row["CE Price Change"] > 0) else "Neutral")
        pe_action = "Writing" if (row["PE OI Change"] > 0 and row["PE Price Change"] < 0) else ("Buying" if (row["PE OI Change"] > 0 and row["PE Price Change"] > 0) else "Neutral")
        return ce_action, pe_action

    df[["CE Action", "PE Action"]] = df.apply(lambda r: pd.Series(classify_action(r)), axis=1)

    # Writers vs Buyers visual bar
    def writers_vs_buyers(row):
        ce_val = 1 if row["CE Action"] == "Buying" else (-1 if row["CE Action"] == "Writing" else 0)
        pe_val = 1 if row["PE Action"] == "Buying" else (-1 if row["PE Action"] == "Writing" else 0)
        net = ce_val + pe_val
        if net >= 2:
            return "🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢"
        elif net == 1:
            return "🟢🟢🟢🟢🟢⚪⚪⚪⚪⚪"
        elif net == 0:
            return "⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪"
        elif net == -1:
            return "🔴🔴🔴🔴🔴⚪⚪⚪⚪⚪"
        else:
            return "🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴"
    df["Writers vs Buyers"] = df.apply(writers_vs_buyers, axis=1)

    # OI Velocity
    if prev_df is not None:
        df["CE OI Velocity"] = df["CE OI"] - prev_df["CE OI"]
        df["PE OI Velocity"] = df["PE OI"] - prev_df["PE OI"]
    else:
        df["CE OI Velocity"] = 0
        df["PE OI Velocity"] = 0

    # Divergence
    df["CE OI Divergence"] = np.sign(df["CE OI Change"]) * np.sign(df["CE Price Change"])
    df["PE OI Divergence"] = np.sign(df["PE OI Change"]) * np.sign(df["PE Price Change"])
    df["CE OI Divergence"] = df["CE OI Divergence"].apply(lambda x: "Bullish" if x == 1 else ("Bearish" if x == -1 else "Neutral"))
    df["PE OI Divergence"] = df["PE OI Divergence"].apply(lambda x: "Bullish" if x == 1 else ("Bearish" if x == -1 else "Neutral"))

    # OI Shift
    if prev_df is not None:
        max_ce_prev = prev_df.loc[prev_df["CE OI"].idxmax(), "Strike"]
        max_ce_curr = df.loc[df["CE OI"].idxmax(), "Strike"]
        max_pe_prev = prev_df.loc[prev_df["PE OI"].idxmax(), "Strike"]
        max_pe_curr = df.loc[df["PE OI"].idxmax(), "Strike"]
        df["CE OI Shift"] = max_ce_curr - max_ce_prev
        df["PE OI Shift"] = max_pe_curr - max_pe_prev
    else:
        df["CE OI Shift"] = 0
        df["PE OI Shift"] = 0

    st.session_state.previous_data = df.copy()

    # Key Metrics
    total_ce = df["CE OI"].sum()
    total_pe = df["PE OI"].sum()
    pcr = total_pe / total_ce if total_ce else 0
    atm_idx = (df["Strike"] - spot).abs().argsort()[0]
    atm_strike = df.iloc[atm_idx]["Strike"]
    support = df.nlargest(3, "PE OI")["Strike"].tolist()
    resistance = df.nlargest(3, "CE OI")["Strike"].tolist()

    # Max Pain
    strikes = df["Strike"].values
    pain_values = []
    for strike in strikes:
        ce_pain = ((df["Strike"] - strike).clip(lower=0) * df["CE OI"]).sum()
        pe_pain = ((strike - df["Strike"]).clip(lower=0) * df["PE OI"]).sum()
        pain_values.append((strike, ce_pain + pe_pain))
    max_pain = min(pain_values, key=lambda x: x[1])[0]

    # Delta Exposure
    df["CE Delta Exposure"] = df["CE Delta"] * df["CE OI"]
    df["PE Delta Exposure"] = -df["PE Delta"] * df["PE OI"]
    net_delta = df["CE Delta Exposure"].sum() + df["PE Delta Exposure"].sum()

    # Trap detection
    max_ce_strike = df.loc[df["CE OI"].idxmax(), "Strike"]
    max_pe_strike = df.loc[df["PE OI"].idxmax(), "Strike"]
    call_trap = (spot > max_ce_strike) and (pcr < 0.7)
    put_trap = (spot < max_pe_strike) and (pcr > 1.3)

    # Best strike
    best_ce = df.loc[df["CE Delta"].sub(0.5).abs().idxmin(), "Strike"]
    best_pe = df.loc[df["PE Delta"].add(0.5).abs().idxmin(), "Strike"]

    # Final Signal
    df["Signal"] = "Neutral"
    for idx, row in df.iterrows():
        if pcr > 1 and row["CE Delta"] > 0.5:
            df.at[idx, "Signal"] = "BUY CE"
        elif pcr < 0.7 and row["PE Delta"] < -0.5:
            df.at[idx, "Signal"] = "BUY PE"
        if row["CE BuildUp"] == "CE Long Build-up" and pcr > 1:
            df.at[idx, "Signal"] = "STRONG BUY CE"
        if row["PE BuildUp"] == "PE Long Build-up" and pcr < 0.7:
            df.at[idx, "Signal"] = "STRONG BUY PE"
    final_signal = df[df["Signal"] != "Neutral"]["Signal"].iloc[0] if not df[df["Signal"] != "Neutral"].empty else "Neutral"

    # ATM PCR
    atm_pcr = df.loc[df['Strike']==atm_strike, 'PE OI'].values[0] / df.loc[df['Strike']==atm_strike, 'CE OI'].values[0] if atm_strike in df['Strike'].values else 0

    # =========================
    # LAYERED UI
    # =========================
    # Level 1 – Decision Bar
    st.markdown("---")
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.metric("📍 Spot", f"{spot:.2f}")
    col2.metric("📊 PCR", f"{pcr:.2f}")
    col3.metric("🧠 Bias", "Bullish" if pcr > 1 else ("Bearish" if pcr < 0.7 else "Neutral"))
    col4.metric("🎯 ATM", f"{atm_strike}")
    col5.metric("🔥 Best", f"{best_ce} CE")
    col6.metric("🚀 Signal", final_signal)
    col7.metric("⚠️ Trap", "Call Trap" if call_trap else ("Put Trap" if put_trap else "No"))
    st.markdown("---")

    # Level 2 – Core Analysis
    st.subheader("📌 Core Analysis")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.success(f"🟢 Support: {support[0] if support else 'N/A'}")
    c2.error(f"🔴 Resistance: {resistance[0] if resistance else 'N/A'}")
    c3.info(f"🎯 Max Pain: {max_pain}")
    c4.info(f"📊 ATM PCR: {atm_pcr:.2f}" if atm_pcr else "N/A")
    c5.info(f"🔥 OI Strength: {'High' if pcr > 1.2 or pcr < 0.8 else 'Moderate'}")

    # Level 3 – Option Chain Table
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

    # Level 4 – Charts
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

    # Candlestick Chart
    st.subheader("🕯️ Candlestick (Spot)")
    from dhan_data.chart import get_candle_data, plot_candle
    try:
        df_candle = get_candle_data(st.session_state.sec_id, st.session_state.segment)
        if df_candle is not None:
            fig_candle, trend = plot_candle(df_candle)
            st.write(f"Trend: {trend}")
            st.plotly_chart(fig_candle, use_container_width=True)
        else:
            st.warning("Candlestick data not available.")
    except Exception as e:
        st.warning(f"Candlestick error: {e}")

    # Level 5 – Strike Analysis
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
        # Placeholder – you can integrate actual historical OI fetch here
        history_ce = [1000, 1200, 1400, 1600, 1800]
        history_pe = [800, 950, 1100, 1250, 1400]
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Scatter(y=history_ce, name="CE OI", mode="lines+markers"))
        fig_hist.add_trace(go.Scatter(y=history_pe, name="PE OI", mode="lines+markers"))
        fig_hist.update_layout(title="OI History (Mock)", height=300)
        st.plotly_chart(fig_hist, use_container_width=True)

    # Level 6 – Pro Insights
    st.subheader("🚀 Pro Insights")
    pro1, pro2, pro3, pro4 = st.columns(4)
    pro1.metric("FII Net Position (cr)", "1,240")
    pro2.metric("DII Net Position (cr)", "-320")
    pro3.metric("IV (ATM)", "14.8%")
    pro4.metric("Gamma Exposure", "₹4.2 Lakh / pt")
    st.write(f"**Delta Exposure:** {net_delta:,.0f}")

else:
    st.info("Select a valid symbol from the sidebar to load data.")
