import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import time
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"
_last_chart_call = 0

def get_candle_data(security_id, segment):
    global _last_chart_call
    now = time.time()
    wait = max(0, 1 - (now - _last_chart_call))
    if wait > 0:
        time.sleep(wait)
    _last_chart_call = time.time()

    # 1. Try intraday (1‑minute) for last 5 days
    try:
        url = f"{BASE_URL}/charts/intraday"
        # Use same exchange logic as historical_data
        if segment == "IDX_I":
            exchange = "IDX_I"
            instrument = "INDEX"
        else:
            exchange = "NSE_EQ"
            instrument = "EQUITY"

        to_date = datetime.now()
        from_date = to_date - timedelta(days=5)
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": exchange,
            "instrument": instrument,
            "interval": "1",
            "oi": False,
            "fromDate": from_date.strftime("%Y-%m-%d %H:%M:%S"),
            "toDate": to_date.strftime("%Y-%m-%d %H:%M:%S")
        }
        res = requests.post(url, headers=get_headers(), json=payload, timeout=10)
        data = res.json()
        if "errorCode" not in data and "data" in data and data["data"]:
            d = data["data"]
            if d.get("timestamp") and len(d["timestamp"]) > 1:
                df = pd.DataFrame({
                    "time": pd.to_datetime(d["timestamp"], unit="s", errors="coerce"),
                    "open": d["open"],
                    "high": d["high"],
                    "low": d["low"],
                    "close": d["close"],
                    "volume": d["volume"] if "volume" in d else [0]*len(d["timestamp"])
                })
                df = df.dropna().sort_values("time")
                return df
    except Exception as e:
        st.warning(f"Intraday chart failed: {e}, trying historical...")

    # 2. Fallback to 5‑minute historical data
    try:
        from dhan_data.historical_data import get_historical
        hist = get_historical(security_id, segment)
        if hist and len(hist) > 1:
            df = pd.DataFrame(hist)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df = df.rename(columns={"time": "time", "open": "open", "high": "high", "low": "low", "close": "close"})
            df["volume"] = 0
            return df
    except Exception as e:
        st.error(f"Historical fallback error: {e}")

    st.error("No candle data available.")
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
        open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color='#00ff88', decreasing_line_color='#ff4d4d'
    ))
    fig.add_trace(go.Scatter(x=df["time"], y=df["EMA21"], name="EMA 21"))
    fig.add_trace(go.Scatter(x=df["time"], y=df["EMA50"], name="EMA 50"))
    fig.update_layout(
        template="plotly_dark", height=600,
        margin=dict(l=5, r=5, t=30, b=5),
        xaxis_rangeslider_visible=False, hovermode="x unified"
    )
    trend = "BULLISH" if df["EMA21"].iloc[-1] > df["EMA50"].iloc[-1] else "BEARISH"
    return fig, trend
