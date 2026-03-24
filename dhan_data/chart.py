import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from core.token_manager import get_token

CHART_URL = "https://api.dhan.co/v2/charts/intraday"

def get_candle_data(security_id, segment):

    token = get_token()
    if not token:
        st.error("No token")
        return None

    # 🔥 FIX: INDEX mapping
    if segment == "IDX_I":
        security_id = 26000
        segment = "NSE_IDX"
        instrument = "INDEX"
    else:
        instrument = "FUTSTK"

    headers = {
        "access-token": token,
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }

    to_date = datetime.now()
    from_date = to_date - timedelta(days=1)

    payload = {
        "securityId": str(security_id),
        "exchangeSegment": segment,
        "instrument": instrument,
        "interval": "5",
        "fromDate": from_date.strftime("%Y-%m-%d %H:%M:%S"),
        "toDate": to_date.strftime("%Y-%m-%d %H:%M:%S")
    }

    res = requests.post(CHART_URL, headers=headers, json=payload)
    data = res.json()

    if "data" not in data:
        st.error(f"Chart API Error: {data}")
        return None

    df = pd.DataFrame({
        "time": data["data"]["time"],
        "open": data["data"]["open"],
        "high": data["data"]["high"],
        "low": data["data"]["low"],
        "close": data["data"]["close"],
        "volume": data["data"]["volume"]
    })

    df["time"] = pd.to_datetime(df["time"])
    return df


def plot_candle(df):
    import plotly.graph_objects as go

    fig = go.Figure(data=[go.Candlestick(
        x=df["time"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"]
    )])

    return fig
