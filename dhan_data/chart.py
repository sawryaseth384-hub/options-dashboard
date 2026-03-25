import pandas as pd
import plotly.graph_objects as go
from dhan_data.historical_data import get_historical

def get_candle_data(security_id, segment):
    data = get_historical(security_id, segment)

    if not data:
        return None

    df = pd.DataFrame({
        "open": data.get("open", []),
        "high": data.get("high", []),
        "low": data.get("low", []),
        "close": data.get("close", []),
        "timestamp": data.get("timestamp", [])
    })

    return df


def plot_candle(df):
    fig = go.Figure(data=[go.Candlestick(
        x=df["timestamp"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"]
    )])

    trend = "UP" if df["close"].iloc[-1] > df["open"].iloc[-1] else "DOWN"

    return fig, trend
