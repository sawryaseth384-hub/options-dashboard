import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px


# =========================
# 🔥 PROCESS DATA
# =========================
def process_option_data(raw_data):
    try:
        if not raw_data:
            return pd.DataFrame(), 0

        data = raw_data.get("data", {})
        spot = data.get("last_price", 0)
        oc = data.get("oc", {})

        rows = []

        for strike, value in oc.items():
            strike_val = float(strike)

            # ATM range filter
            if abs(strike_val - spot) > 1000:
                continue

            ce = value.get("ce") or {}
            pe = value.get("pe") or {}

            rows.append({
                "Strike": int(strike_val),

                "CE OI": ce.get("oi", 0),
                "CE LTP": ce.get("last_price", 0),
                "CE Delta": ce.get("greeks", {}).get("delta", 0),
                "CE IV": ce.get("implied_volatility", 0),

                "PE OI": pe.get("oi", 0),
                "PE LTP": pe.get("last_price", 0),
                "PE Delta": pe.get("greeks", {}).get("delta", 0),
                "PE IV": pe.get("implied_volatility", 0),
            })

        df = pd.DataFrame(rows)

        if df.empty:
            return df, spot

        df = df.sort_values("Strike").reset_index(drop=True)

        return df, spot

    except Exception as e:
        print("PROCESS ERROR:", e)
        return pd.DataFrame(), 0


# =========================
# 📊 PCR
# =========================
def calculate_pcr(df):
    try:
        if df is None or df.empty:
            return 0

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
        if df is None or df.empty:
            return 0, 0

        support = df.loc[df["PE OI"].idxmax(), "Strike"]
        resistance = df.loc[df["CE OI"].idxmax(), "Strike"]

        return int(support), int(resistance)
    except:
        return 0, 0


# =========================
# 🚀 SIGNAL
# =========================
def get_signal(pcr):
    try:
        if pcr > 1.2:
            return "📈 Bullish"
        elif pcr < 0.8:
            return "📉 Bearish"
        return "⚖️ Sideways"
    except:
        return "N/A"


# =========================
# 🎯 ATM
# =========================
def get_atm_strike(df, spot):
    try:
        if df is None or df.empty:
            return 0

        return int(df.iloc[(df["Strike"] - spot).abs().argsort()[:1]]["Strike"].values[0])
    except:
        return 0


# =========================
# 🎨 HIGHLIGHT ATM
# =========================
def highlight_atm(row, atm):
    try:
        if row["Strike"] == atm:
            return ["background-color: #00FFAA"] * len(row)
        return [""] * len(row)
    except:
        return [""] * len(row)


# =========================
# 🔥 LEVEL 3 – OI CHANGE
# =========================
def calculate_oi_change(df, prev_df):
    try:
        if df is None or df.empty:
            return df

        if prev_df is None or prev_df.empty:
            return df

        # size mismatch protection
        if len(df) != len(prev_df):
            return df

        df["CE OI Change"] = df["CE OI"] - prev_df["CE OI"]
        df["PE OI Change"] = df["PE OI"] - prev_df["PE OI"]

        return df
    except:
        return df


def get_dominance(pcr):
    try:
        if pcr > 1.2:
            return "🟢 PUT WRITING"
        elif pcr < 0.8:
            return "🔴 CALL WRITING"
        return "⚖️ Neutral"
    except:
        return "N/A"


# =========================
# 🔥 LEVEL 4 – TREND + HEATMAP
# =========================
def get_trend(df):
    try:
        if df is None or df.empty:
            return "N/A"

        avg_delta = df["CE Delta"].mean()

        if avg_delta > 0.6:
            return "📈 Uptrend"
        elif avg_delta < 0.4:
            return "📉 Downtrend"
        return "⚖️ Sideways"
    except:
        return "N/A"


def plot_oi_heatmap(df):
    try:
        if df is None or df.empty:
            return go.Figure()

        heat_df = df[["CE OI", "PE OI"]].T

        fig = px.imshow(
            heat_df,
            labels=dict(x="Strike", y="Type", color="OI"),
            x=df["Strike"]
        )
        return fig

    except Exception as e:
        print("Heatmap Error:", e)
        return go.Figure()


# =========================
# 🔥 LEVEL 5 – AI + STRATEGY
# =========================
def ai_signal(pcr, trend):
    try:
        if pcr > 1.2 and "Uptrend" in trend:
            return "🔥 STRONG BUY CALL"
        elif pcr < 0.8 and "Downtrend" in trend:
            return "🔥 STRONG BUY PUT"
        return "⚖️ WAIT"
    except:
        return "WAIT"


def build_strategy(signal, atm):
    try:
        if "CALL" in signal:
            return f"Buy {atm} CE"
        elif "PUT" in signal:
            return f"Buy {atm} PE"
        return "No Trade"
    except:
        return "No Trade"


def plot_payoff(strike):
    try:
        if strike == 0:
            return go.Figure()

        price = np.arange(strike - 500, strike + 500, 10)
        payoff = np.maximum(price - strike, 0)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=price, y=payoff, name="Payoff"))

        return fig
    except:
        return go.Figure()
