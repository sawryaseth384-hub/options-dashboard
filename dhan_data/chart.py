import requests
import pandas as pd
from datetime import datetime, timedelta
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

# =========================
# GET CANDLE DATA
# =========================
def get_candle_data(security_id, segment):

    # 🔥 INDEX (NIFTY / BANKNIFTY)
    if segment == "IDX_I":

        index_map = {
            13: "26000",   # NIFTY
            25: "26009",   # BANKNIFTY
            27: "26037"    # FINNIFTY
        }

        chart_id = index_map.get(security_id)

        if not chart_id:
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

        res = requests.post(
            f"{BASE_URL}/charts/intraday",
            headers=get_headers(),
            json=payload
        )

        data = res.json()

        if "data" not in data:
            return None

        d = data["data"]

        df = pd.DataFrame({
            "time": pd.to_datetime(d["timestamp"], unit="s"),
            "open": d["open"],
            "high": d["high"],
            "low": d["low"],
            "close": d["close"],
            "volume": d.get("volume", [0]*len(d["timestamp"]))
        })

        return df.sort_values("time")

    # 🔥 STOCK / FNO
    else:
        try:
            from dhan_data.historical_data import get_historical

            hist = get_historical(security_id, segment)

            if hist:
                df = pd.DataFrame(hist)
                df["time"] = pd.to_datetime(df["time"], unit="s")
                return df.sort_values("time")

        except:
            return None

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
        xaxis_rangeslider_visible=False
    )

    trend = "BULLISH" if df["EMA21"].iloc[-1] > df["EMA50"].iloc[-1] else "BEARISH"

    return fig, trend
