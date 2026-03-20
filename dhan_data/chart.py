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
    if segment in ["IDX_I", "D"]:
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

        # ❗ RAW DEBUG (optional)
        # st.write(data)

        if not data or "open" not in data:
            return None

        # =========================
        # 🔥 FAST FLATTEN
        # =========================
        def flatten(arr):
            return [item for sub in arr for item in sub]

        open_ = flatten(data.get("open", []))
        high_ = flatten(data.get("high", []))
        low_ = flatten(data.get("low", []))
        close_ = flatten(data.get("close", []))
        volume_ = flatten(data.get("volume", []))
        time_ = flatten(data.get("timestamp", []))

        if len(time_) == 0:
            return None

        df = pd.DataFrame({
            "time": pd.to_datetime(time_, errors="coerce"),
            "open": open_,
            "high": high_,
            "low": low_,
            "close": close_,
            "volume": volume_,
        })

        # साफ data
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

    # Trend
    if df["EMA21"].iloc[-1] > df["EMA50"].iloc[-1]:
        trend = "BULLISH"
    else:
        trend = "BEARISH"

    return df, trend


# =========================
# 📊 PLOT CANDLE (CLEAN)
# =========================
def plot_candle(df):
    import plotly.graph_objects as go

    fig = go.Figure()

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

    fig.update_layout(
        template="plotly_dark",
        height=550,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(showgrid=False, rangeslider=dict(visible=False)),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
    )

    return fig
