import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

# =========================
# FIX: CHART ID MAPPING
# =========================
def get_chart_id(security_id):
    if security_id == 13:
        return "26000", "NSE_IDX"   # NIFTY
    elif security_id == 25:
        return "26009", "NSE_IDX"   # BANKNIFTY
    elif security_id == 27:
        return "26037", "NSE_IDX"   # FINNIFTY
    else:
        return str(security_id), "NSE_EQ"


# =========================
# GET CANDLE DATA
# =========================
def get_candle_data(security_id, segment):

    chart_id, chart_seg = get_chart_id(security_id)

    try:
        url = f"{BASE_URL}/charts/intraday"

        to_date = datetime.now()
        from_date = to_date - timedelta(days=5)

        payload = {
            "securityId": chart_id,
            "exchangeSegment": chart_seg,
            "instrument": "INDEX" if chart_seg == "NSE_IDX" else "EQUITY",
            "interval": "1",
            "oi": False,
            "fromDate": from_date.strftime("%Y-%m-%d %H:%M:%S"),
            "toDate": to_date.strftime("%Y-%m-%d %H:%M:%S")
        }

        res = requests.post(url, headers=get_headers(), json=payload, timeout=10)
        data = res.json()

        if "data" not in data:
            st.error(f"Chart API Error: {data}")
            return None

        d = data["data"]

        if not d.get("timestamp"):
            return None

        df = pd.DataFrame({
            "time": pd.to_datetime(d["timestamp"], unit="s"),
            "open": d["open"],
            "high": d["high"],
            "low": d["low"],
            "close": d["close"],
            "volume": d.get("volume", [0]*len(d["timestamp"]))
        })

        df = df.sort_values("time")
        return df

    except Exception as e:
        st.error(f"Chart Error: {e}")
        return None


# =========================
# INDICATORS
# =========================
def add_indicators(df):
    df["EMA21"] = df["close"].ewm(span=21).mean()
    df["EMA50"] = df["close"].ewm(span=50).mean()
    return df


# =========================
# PLOT
# =========================
def plot_candle(df):
    import plotly.graph_objects as go

    df = add_indicators(df)

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df["time"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"]
    ))

    fig.add_trace(go.Scatter(x=df["time"], y=df["EMA21"], name="EMA21"))
    fig.add_trace(go.Scatter(x=df["time"], y=df["EMA50"], name="EMA50"))

    return fig
