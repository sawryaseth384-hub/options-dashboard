import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dhan_data.instruments import get_symbol_data
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain
from dhan_data.market_quote import get_ltp
from core.token_manager import get_headers
from dashboard import (
    render_header, render_decision_bar, render_core_analysis,
    render_option_chain_table, render_charts, render_candlestick,
    render_strike_analysis, render_pro_insights
)

# =========================
# STYLE – Dark Theme
# =========================
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
# HARDCODED FALLBACKS
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

# =========================
# FETCH SPOT PRICES FOR HEADER
# =========================
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

    if st.session_state.sec_id is None:
        sec_id, seg = resolve_symbol(st.session_state.symbol)
        st.session_state.sec_id = sec_id
        st.session_state.segment = seg
        if sec_id:
            st.success(f"✅ {st.session_state.symbol} → ID: {sec_id}, Segment: {seg}")

    if st.session_state.sec_id:
        expiry_list = []
        try:
            exp_data = get_expiry(st.session_state.sec_id)
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
# TOP BAR (NIFTY & BANKNIFTY SPOT)
# =========================
nifty_spot = get_spot_for("NIFTY")
banknifty_spot = get_spot_for("BANKNIFTY")
render_header(nifty_spot, banknifty_spot)

# =========================
# MAIN DASHBOARD (if data available)
# =========================
if st.session_state.sec_id and st.session_state.expiry:
    @st.cache_data(ttl=60)
    def fetch_chain(sec_id, expiry, segment):
        return get_option_chain(sec_id, expiry, segment)

    data = fetch_chain(st.session_state.sec_id, st.session_state.expiry, st.session_state.segment)
    if not data or "data" not in data:
        st.error("No option chain data. Check symbol/expiry.")
        st.stop()

    # Process raw data (same as before)
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
            "PE OI": pe.get("oi", 0),
            "PE LTP": pe.get("last_price", 0),
            "PE Delta": pe.get("greeks", {}).get("delta", 0),
        })
    df = pd.DataFrame(rows).sort_values("Strike")
    prev_df = st.session_state.previous_data

    # Advanced indicators (unchanged from previous version)
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
    # RENDER DASHBOARD FROM MODULE
    # =========================
    render_decision_bar(spot, pcr, atm_strike, best_ce, final_signal, call_trap, put_trap)
    render_core_analysis(support, resistance, max_pain, atm_pcr, pcr)
    render_option_chain_table(df)
    render_charts(df, support, resistance, spot)
    render_candlestick(st.session_state.sec_id, st.session_state.segment)
    render_strike_analysis(df, st.session_state.sec_id)
    render_pro_insights(net_delta)

else:
    st.info("Select a valid symbol from the sidebar to load data.")
