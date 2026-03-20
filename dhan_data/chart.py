import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

BASE_URL = "https://api.dhan.co/v2"


def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }


# 🔥 SEGMENT FIX
def map_segment(segment):
    if segment == "IDX_I":
        return "NSE_FNO"
    elif segment == "D":
        return "NSE_FNO"
    else:
        return "NSE_EQ"


# 🔥 INSTRUMENT FIX
def get_instrument_type(segment):
    if segment in ["IDX_I", "D"]:
        return "FUTIDX"
    else:
        return "EQUITY"


# =========================
# 📈 GET CANDLE DATA
# =========================
def get_candle_data(security_id, segment):

    try:
        url = f"{BASE_URL}/charts/intraday"

        mapped_segment = map_segment(segment)
        instrument = get_instrument_type(segment)

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

        # 🔍 DEBUG
        st.write("CHART RAW:", data)

        if "open" not in data:
            return None

        df = pd.DataFrame({
            "open": data["open"],
            "high": data["high"],
            "low": data["low"],
            "close": data["close"],
            "volume": data["volume"],
            "time": pd.to_datetime(data["timestamp"], unit="s")
        })

        return df

    except Exception as e:
        st.error(f"Chart Error: {e}")
        return None


# =========================
# 📊 PLOT CANDLE
# =========================
def plot_candle(df):
    import plotly.graph_objects as go

    fig = go.Figure(data=[
        go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"]
        )
    ])

    fig.update_layout(height=500)
    return fig
