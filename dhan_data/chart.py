import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

BASE_URL = "https://api.dhan.co/v2"


def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }


# =========================
# 📊 FETCH HISTORICAL DATA
# =========================
def get_candle_data(security_id, segment):
    try:
        url = f"{BASE_URL}/charts/historical"

        payload = {
            "securityId": security_id,
            "exchangeSegment": segment,
            "interval": "5"  # 5 min candle
        }

        res = requests.post(url, headers=get_headers(), json=payload)
        data = res.json()

        if "data" not in data:
            return None

        df = pd.DataFrame(data["data"])

        df["datetime"] = pd.to_datetime(df["startTime"])

        return df

    except Exception as e:
        st.error(f"Chart Error: {e}")
        return None


# =========================
# 📈 PLOT CANDLE
# =========================
def plot_candle(df):
    fig = go.Figure(data=[go.Candlestick(
        x=df["datetime"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"]
    )])

    fig.update_layout(
        title="Live Chart",
        xaxis_title="Time",
        yaxis_title="Price",
        template="plotly_dark"
    )

    return fig
