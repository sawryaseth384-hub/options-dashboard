import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

BASE_URL = "https://api.dhan.co/v2"


# =========================
# 🔐 HEADERS
# =========================
def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }


# =========================
# 🔁 SEGMENT MAP (FINAL FIX)
# =========================
def map_segment(segment):

    # 🔥 INDEX FIX (MOST IMPORTANT)
    if segment in ["IDX_I", "I"]:
        return "NSE_EQ"   # ✅ FINAL FIX

    elif segment == "D":
        return "NSE_FNO"

    elif segment == "E":
        return "NSE_EQ"

    else:
        return "NSE_EQ"


# =========================
# 📦 INSTRUMENT TYPE
# =========================
def get_instrument_type(segment):

    if segment in ["IDX_I", "I"]:
        return "EQUITY"

    elif segment == "D":
        return "FUTSTK"

    elif segment == "E":
        return "EQUITY"

    else:
        return "EQUITY"


# =========================
# 🔥 SAFE FLATTEN
# =========================
def flatten(arr):
    flat = []

    if not isinstance(arr, list):
        return [arr]

    for sub in arr:
        if isinstance(sub, list):
            flat.extend(sub)
        else:
            flat.append(sub)

    return flat


# =========================
# 📈 GET CANDLE DATA
# =========================
def get_candle_data(security_id, segment):

    try:
        url = f"{BASE_URL}/charts/intraday"

        mapped_segment = map_segment(segment)
        instrument = get_instrument_type(segment)

        # 🔥 FIXED TIME RANGE (MARKET HOURS)
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        from_date = f"{today} 09:15:00"
        to_date = f"{today} 15:30:00"

        payload = {
            "securityId": str(security_id),
            "exchangeSegment": mapped_segment,
            "instrument": instrument,
            "interval": "1",
            "oi": False,
            "fromDate": from_date,
            "toDate": to_date
        }

        res = requests.post(url, headers=get_headers(), json=payload)
        data = res.json()

        # 🔍 DEBUG
        st.write("RAW:", data)

        # ❌ ERROR HANDLE
        if "errorCode" in data:
            st.error(data.get("errorMessage"))
            return None

        if not data or "open" not in data:
            st.warning("No data from API")
            return None

        # 🔥 SAFE EXTRACT
        open_ = flatten(data["open"])
        high_ = flatten(data["high"])
        low_ = flatten(data["low"])
        close_ = flatten(data["close"])
        time_ = flatten(data["timestamp"])

        # 🔥 LENGTH MATCH
        min_len = min(len(open_), len(high_), len(low_), len(close_), len(time_))

        df = pd.DataFrame({
            "time": pd.to_datetime(time_[:min_len], unit="s"),
            "open": open_[:min_len],
            "high": high_[:min_len],
            "low": low_[:min_len],
            "close": close_[:min_len],
        })

        df = df.dropna().sort_values("time")

        if df.empty:
            st.warning("Empty dataframe")
            return None

        return df

    except Exception as e:
        st.error(f"Fetch Error: {e}")
        return None
# =========================
# 📊 INDICATORS
# =========================
def add_indicators(df):

    df["EMA21"] = df["close"].ewm(span=21).mean()
    df["EMA50"] = df["close"].ewm(span=50).mean()

    trend = "BULLISH" if df["EMA21"].iloc[-1] > df["EMA50"].iloc[-1] else "BEARISH"

    return df, trend


# =========================
# 📊 PLOT CHART
# =========================
def plot_candle(df):
    import plotly.graph_objects as go

    df, trend = add_indicators(df)

    fig = go.Figure()

    # 🕯️ candles
    fig.add_trace(go.Candlestick(
        x=df["time"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        increasing_line_color='#00ff88',
        decreasing_line_color='#ff4d4d',
        name="Price"
    ))

    # EMA 21
    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["EMA21"],
        name="EMA 21"
    ))

    # EMA 50
    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["EMA50"],
        name="EMA 50"
    ))

    fig.update_layout(
        template="plotly_dark",
        height=600,
        margin=dict(l=5, r=5, t=30, b=5),
        xaxis=dict(showgrid=False, rangeslider=dict(visible=False)),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
        hovermode="x unified"
    )

    return fig, trend
