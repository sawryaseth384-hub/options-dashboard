import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px


# =========================
# 🔥 PROCESS DATA
# =========================
def process_option_data(raw_data):
    try:
        data = raw_data.get("data", {})
        spot = data.get("last_price", 0)
        oc = data.get("oc", {})

        rows = []

        for strike, value in oc.items():
            strike_val = float(strike)

            if abs(strike_val - spot) > 1000:
                continue

            ce = value.get("ce")
            pe = value.get("pe")

            rows.append({
                "Strike": int(strike_val),

                "CE OI": ce["oi"] if ce else 0,
                "CE LTP": ce["last_price"] if ce else 0,
                "CE Delta": ce.get("greeks", {}).get("delta", 0) if ce else 0,
                "CE IV": ce.get("implied_volatility", 0) if ce else 0,

                "PE OI": pe["oi"] if pe else 0,
                "PE LTP": pe["last_price"] if pe else 0,
                "PE Delta": pe.get("greeks", {}).get("delta", 0) if pe else 0,
                "PE IV": pe.get("implied_volatility", 0) if pe else 0,
            })

        df = pd.DataFrame(rows)

        if df.empty:
            return df, spot

        return df.sort_values("Strike").reset_index(drop=True), spot

    except Exception as e:
        print("PROCESS ERROR:", e)
        return pd.DataFrame(), 0


# =========================
# 📊 PCR
# =========================
def calculate_pcr(df):
    try:
        ce = df["CE OI"].sum()
        pe = df["PE OI"].sum()
        return round(pe / ce, 2) if ce != 0 else 0
    except:
        return 0


# =========================
# 🟢 SUPPORT / 🔴 RESISTANCE
# =========================
def get_support_resistance(df):
    try:
        support = df.loc[df["PE OI"].idxmax(), "Strike"]
        resistance = df.loc[df["CE OI"].idxmax(), "Strike"]
        return int(support), int(resistance)
    except:
        return 0, 0


# =========================
# 🚀 SIGNAL
# =========================
def get_signal(pcr):
    if pcr > 1.2:
        return "📈 Bullish"
    elif pcr < 0.8:
        return "📉 Bearish"
    return "⚖️ Sideways"


# =========================
# 🎯 ATM
# =========================
def get_atm_strike(df, spot):
    try:
        return int(df.iloc[(df["Strike"] - spot).abs().argsort()[:1]]["Strike"].values[0])
    except:
        return 0


# =========================
# 🎨 HIGHLIGHT
# =========================
def highlight_atm(row, atm):
    if row["Strike"] == atm:
        return ["background-color: #00FFAA"] * len(row)
    return [""] * len(row)


# =========================
# 🔥 LEVEL 3
# =========================
def calculate_oi_change(df, prev_df):
    try:
        if prev_df is None:
            return df

        df["CE OI Change"] = df["CE OI"] - prev_df["CE OI"]
        df["PE OI Change"] = df["PE OI"] - prev_df["PE OI"]

        return df
    except:
        return df


def get_dominance(pcr):
    if pcr > 1.2:
        return "🟢 PUT WRITING"
    elif pcr < 0.8:
        return "🔴 CALL WRITING"
    return "⚖️ Neutral"


# =========================
# 🔥 LEVEL 4
# =========================
def get_trend(df):
    try:
        avg_delta = df["CE Delta"].mean()
        if avg_delta > 0.6:
            return "📈 Uptrend"
        elif avg_delta < 0.4:
            return "📉 Downtrend"
        return "⚖️ Sideways"
    except:
        return "N/A"


def plot_oi_heatmap(df):
    fig = px.imshow(
        df[["CE OI", "PE OI"]].T,
        labels=dict(x="Strike", y="Type", color="OI"),
        x=df["Strike"]
    )
    return fig


# =========================
# 🔥 LEVEL 5
# =========================
def ai_signal(pcr, trend):
    if pcr > 1.2 and "Uptrend" in trend:
        return "🔥 STRONG BUY CALL"
    elif pcr < 0.8 and "Downtrend" in trend:
        return "🔥 STRONG BUY PUT"
    return "⚖️ WAIT"


def build_strategy(signal, atm):
    if "CALL" in signal:
        return f"Buy {atm} CE"
    elif "PUT" in signal:
        return f"Buy {atm} PE"
    return "No Trade"


def plot_payoff(strike):
    price = np.arange(strike - 500, strike + 500, 10)
    payoff = np.maximum(price - strike, 0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=price, y=payoff))
    return fig
