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
# 🔁 SEGMENT MAP (FINAL)
# =========================
def map_segment(segment):
    if segment == "IDX_I":
        return "NSE_FNO"
    elif segment == "D":
        return "NSE_FNO"
    elif segment == "E":
        return "NSE_EQ"
    else:
        return "NSE_EQ"


# =========================
# 📦 INSTRUMENT TYPE (FINAL)
# =========================
def get_instrument_type(segment):
    if segment == "IDX_I":
        return "FUTIDX"
    elif segment == "D":
        return "FUTSTK"
    elif segment == "E":
        return "EQUITY"
    else:
        return "EQUITY"


# =========================
# 🔥 SAFE FLATTEN (NO ERROR)
# =========================
def flatten(arr):
    if not isinstance(arr, list):
        return [arr]

    flat = []
    for sub in arr:
        if isinstance(sub, list):
            flat.extend(sub)
        else:
            flat.append(sub)
    return flat


# =========================
# 📈 GET CANDLE DATA (FINAL)
# =========================
def get_candle_data(security_id, segment):

    try:
        url = f"{BASE_URL}/charts/intraday"

        mapped_segment = map_segment(segment)
        instrument = get_instrument_type(segment)

        # 🔍 DEBUG (remove later)
        st.write("SECURITY:", security_id)
        st.write("SEGMENT:", segment)
        st.write("MAPPED:", mapped_segment)
        st.write("INSTRUMENT:", instrument)

        to_date = datetime.now()
        from_date = to_date - timedelta(days=1)

        payload = {
            "securityId": str(security_id),
            "exchangeSegment": mapped_segment,
            "instrument": instrument,
            "interval": "5",
            "oi": False,
            "fromDate": from_date.strftime("%Y-%m-%d %H:%M:%S"),
            "toDate": to_date.strftime("%Y-%m-%d %H:%M:%S")
        }

        res = requests.post(url, headers=get_headers(), json=payload)
        data = res.json()

        # 🔍 DEBUG RAW
        st.write("RAW DATA:", data)

        if not data or "open" not in data:
            return None

        open_ = flatten(data.get("open", []))
        high_ = flatten(data.get("high", []))
        low_ = flatten(data.get("low", []))
        close_ = flatten(data.get("close", []))
        time_ = flatten(data.get("timestamp", []))

        if len(time_) == 0:
            return None

        # 🔥 LENGTH FIX
        min_len = min(len(open_), len(high_), len(low_), len(close_), len(time_))

        open_ = open_[:min_len]
        high_ = high_[:min_len]
        low_ = low_[:min_len]
        close_ = close_[:min_len]
        time_ = time_[:min_len]

        # 🔥 TIME FIX
        time_ = pd.to_datetime(time_, errors="coerce", unit="s")

        df = pd.DataFrame({
            "time": time_,
            "open": open_,
            "high": high_,
            "low": low_,
            "close": close_,
        })

        df = df.dropna()
        df = df.sort_values("time")

        return df

    except Exception as e:
        st.error(f"Chart Error: {e}")
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
# 📊 PLOT CANDLE (TRADINGVIEW STYLE)
# =========================
def plot_candle(df):
    import plotly.graph_objects as go

    df, trend = add_indicators(df)

    fig = go.Figure()

    # 🕯️ Candles
    fig.add_trace(go.Candlestick(
        x=df["time"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        increasing_line_color='#00ff88',
        decreasing_line_color='#ff4d4d'
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
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.03)"),
        hovermode="x unified"
    )

    return fig, trend
