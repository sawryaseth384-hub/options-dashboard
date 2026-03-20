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
    if segment == "IDX_I":
        return "NSE_FNO"
    elif segment == "D":
        return "NSE_FNO"
    else:
        return "NSE_EQ"


# =========================
# 📦 INSTRUMENT TYPE
# =========================
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

        if not data or "open" not in data:
            return None

        # =========================
        # 🔥 FLATTEN FUNCTION
        # =========================
        def flatten(arr):
            flat = []
            for i in arr:
                if isinstance(i, list):
                    flat.extend(i)
                else:
                    flat.append(i)
            return flat

        open_ = flatten(data.get("open", []))
        high_ = flatten(data.get("high", []))
        low_ = flatten(data.get("low", []))
        close_ = flatten(data.get("close", []))
        volume_ = flatten(data.get("volume", []))
        time_ = flatten(data.get("timestamp", []))

        if len(time_) == 0:
            return None

        df = pd.DataFrame({
            "open": open_,
            "high": high_,
            "low": low_,
            "close": close_,
            "volume": volume_,
            "time": pd.to_datetime(time_, unit="s")
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

    fig.update_layout(
        height=500,
        xaxis_rangeslider_visible=False
    )

    return fig
