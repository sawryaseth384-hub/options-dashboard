import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import time

BASE_URL = "https://api.dhan.co/v2"

_last_chart_call = 0

def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }

def map_segment(segment):
    if segment in ["IDX_I", "I", "D"]:
        return "NSE_FNO"
    else:
        return "NSE_EQ"

def get_instrument(segment):
    if segment in ["IDX_I", "I"]:
        return "INDEX"
    elif segment == "D":
        return "FUTSTK"
    else:
        return "EQUITY"

def get_candle_data(security_id, segment):
    global _last_chart_call

    # Rate limiting
    now = time.time()
    wait = max(0, 1 - (now - _last_chart_call))
    if wait > 0:
        time.sleep(wait)
    _last_chart_call = time.time()

    try:
        url = f"{BASE_URL}/charts/intraday"

        mapped_segment = map_segment(segment)
        instrument = get_instrument(segment)

        to_date = datetime.now()
        from_date = to_date - timedelta(days=3)

        payload = {
            "securityId": str(security_id),
            "exchangeSegment": mapped_segment,
            "instrument": instrument,
            "interval": "1",
            "oi": False,
            "fromDate": from_date.strftime("%Y-%m-%d %H:%M:%S"),
            "toDate": to_date.strftime("%Y-%m-%d %H:%M:%S")
        }

        res = requests.post(url, headers=get_headers(), json=payload)
        data = res.json()

        if "errorCode" in data:
            st.error(data.get("errorMessage"))
            return None

        # 🔥 FIX: Check for "data" key
        if "data" not in data or not data["data"]:
            return None

        d = data["data"]

        df = pd.DataFrame({
            "time": pd.to_datetime(d["timestamp"], unit="s", errors="coerce"),
            "open": d["open"],
            "high": d["high"],
            "low": d["low"],
            "close": d["close"],
            "volume": d["volume"]
        })

        df = df.dropna()
        df = df.sort_values("time")
        return df

    except Exception as e:
        st.error(f"Chart Error: {e}")
        return None

def add_indicators(df):
    df["EMA21"] = df["close"].ewm(span=21).mean()
    df["EMA50"] = df["close"].ewm(span=50).mean()
    return df

def plot_candle(df):
    import plotly.graph_objects as go

    df = add_indicators(df)

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["time"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        increasing_line_color='#00ff88',
        decreasing_line_color='#ff4d4d'
    ))
    fig.add_trace(go.Scatter(x=df["time"], y=df["EMA21"], name="EMA 21"))
    fig.add_trace(go.Scatter(x=df["time"], y=df["EMA50"], name="EMA 50"))

    fig.update_layout(
        template="plotly_dark",
        height=600,
        margin=dict(l=5, r=5, t=30, b=5),
        xaxis_rangeslider_visible=False,
        hovermode="x unified"
    )

    trend = "BULLISH" if df["EMA21"].iloc[-1] > df["EMA50"].iloc[-1] else "BEARISH"
    return fig, trend
