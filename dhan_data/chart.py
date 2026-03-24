import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import time
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"
_last_chart_call = 0


# =========================
# GET CANDLE DATA
# =========================
def get_candle_data(security_id, segment):
    global _last_chart_call

    # 🔒 Rate limit safety
    now = time.time()
    wait = max(0, 1 - (now - _last_chart_call))
    if wait > 0:
        time.sleep(wait)
    _last_chart_call = time.time()

    try:
        # =========================
        # 🔥 INDEX FIX (IMPORTANT)
        # =========================
        if segment == "IDX_I":

            index_map = {
                13: "26000",   # NIFTY
                25: "26009",   # BANKNIFTY
                27: "26037"    # FINNIFTY
            }

            chart_id = index_map.get(security_id)

            if not chart_id:
                st.warning("Invalid index mapping")
                return None

            payload = {
                "securityId": chart_id,
                "exchangeSegment": "NSE_IDX",
                "instrument": "INDEX",
                "interval": "5",
                "oi": False,
                "fromDate": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
                "toDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        # =========================
        # 🔥 STOCK / FNO
        # =========================
        else:
            payload = {
                "securityId": str(security_id),
                "exchangeSegment": "NSE_EQ",
                "instrument": "EQUITY",
                "interval": "5",
                "oi": False,
                "fromDate": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
                "toDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        # =========================
        # API CALL
        # =========================
        res = requests.post(
            f"{BASE_URL}/charts/intraday",
            headers=get_headers(),
            json=payload,
            timeout=10
        )

        data = res.json()

        # =========================
        # ERROR CHECK
        # =========================
        if "errorCode" in data:
            st.warning(data.get("errorMessage"))
            return None

        if "data" not in data or not data["data"]:
            st.warning("No candle data returned")
            return None

        d = data["data"]

        if not d.get("timestamp"):
            return None

        # =========================
        # DATAFRAME BUILD
        # =========================
        df = pd.DataFrame({
            "time": pd.to_datetime(d["timestamp"], unit="s", errors="coerce"),
            "open": d["open"],
            "high": d["high"],
            "low": d["low"],
            "close": d["close"],
            "volume": d.get("volume", [0]*len(d["timestamp"]))
        })

        df = df.dropna().sort_values("time")

        return df

    except Exception as e:
        st.error(f"Chart Error: {e}")
        return None


# =========================
# ADD INDICATORS
# =========================
def add_indicators(df):
    df["EMA21"] = df["close"].ewm(span=21).mean()
    df["EMA50"] = df["close"].ewm(span=50).mean()
    return df


# =========================
# PLOT CANDLE
# =========================
def plot_candle(df):
    import plotly.graph_objects as go

    if df is None or df.empty:
        return None, "NO DATA"

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
