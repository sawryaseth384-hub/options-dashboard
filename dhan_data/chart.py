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
# 🔁 SEGMENT MAP
# =========================
def map_segment(segment):
    if segment in ["IDX_I", "I", "D"]:
        return "NSE_FNO"
    else:
        return "NSE_EQ"


# =========================
# 📦 INSTRUMENT TYPE
# =========================
def get_instrument(segment):
    if segment in ["IDX_I", "I"]:
        return "INDEX"
    elif segment == "D":
        return "FUTSTK"
    else:
        return "EQUITY"


# =========================
# 🔥 HISTORICAL DATA (BEST)
# =========================
def get_candle_data(security_id, segment):

    try:
        url = f"{BASE_URL}/charts/intraday"

        mapped_segment = map_segment(segment)
        instrument = get_instrument(segment)

        to_date = datetime.now()
        from_date = to_date - timedelta(days=3)   # more candles

        payload = {
            "securityId": str(security_id),
            "exchangeSegment": mapped_segment,
            "instrument": instrument,
            "interval": "1",   # 🔥 1 min (best)
            "oi": False,
            "fromDate": from_date.strftime("%Y-%m-%d %H:%M:%S"),
            "toDate": to_date.strftime("%Y-%m-%d %H:%M:%S")
        }

        res = requests.post(url, headers=get_headers(), json=payload)
        data = res.json()

        if "errorCode" in data:
            st.error(data.get("errorMessage"))
            return None

        if not data or "open" not in data:
            return None

        # =========================
        # 🔥 CLEAN DATA
        # =========================
        df = pd.DataFrame({
            "time": pd.to_datetime(data["timestamp"], unit="s", errors="coerce"),
            "open": data["open"],
            "high": data["high"],
            "low": data["low"],
            "close": data["close"],
            "volume": data["volume"]
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

    return df


# =========================
# 📊 PLOT (TRADINGVIEW STYLE)
# =========================
def plot_candle(df):
    import plotly.graph_objects as go

    df = add_indicators(df)

    fig = go.Figure()

    # candles
    fig.add_trace(go.Candlestick(
        x=df["time"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        increasing_line_color='#00ff88',
        decreasing_line_color='#ff4d4d'
    ))

    # EMA21
    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["EMA21"],
        name="EMA 21"
    ))

    # EMA50
    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["EMA50"],
        name="EMA 50"
    ))

    fig.update_layout(
        template="plotly_dark",
        height=600,
        margin=dict(l=5, r=5, t=30, b=5),
        xaxis_rangeslider_visible=False,
        hovermode="x unified"
    )

    trend = "BULLISH" if df["EMA21"].iloc[-1] > df["EMA50"].iloc[-1] else "BEARISH"

    return fig, trend
