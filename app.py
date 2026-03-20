import pandas as pd


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

            if not ce and not pe:
                continue

            rows.append({
                "Strike": int(strike_val),
                "CE OI": ce["oi"] if ce else 0,
                "CE LTP": ce["last_price"] if ce else 0,
                "CE Delta": ce.get("greeks", {}).get("delta", 0) if ce else 0,
                "PE OI": pe["oi"] if pe else 0,
                "PE LTP": pe["last_price"] if pe else 0,
                "PE Delta": pe.get("greeks", {}).get("delta", 0) if pe else 0,
            })

        df = pd.DataFrame(rows)

        if df.empty:
            return df, spot

        return df.sort_values("Strike").reset_index(drop=True), spot

    except Exception as e:
        print("PROCESS ERROR:", e)
        return pd.DataFrame(), 0


# PCR
def calculate_pcr(df):
    try:
        ce = df["CE OI"].sum()
        pe = df["PE OI"].sum()
        return round(pe / ce, 2) if ce != 0 else 0
    except:
        return 0


# Support / Resistance
def get_support_resistance(df):
    try:
        support = df.loc[df["PE OI"].idxmax(), "Strike"]
        resistance = df.loc[df["CE OI"].idxmax(), "Strike"]
        return int(support), int(resistance)
    except:
        return 0, 0


# Signal
def get_signal(pcr):
    if pcr > 1.2:
        return "📈 Bullish"
    elif pcr < 0.8:
        return "📉 Bearish"
    return "⚖️ Sideways"


# ATM
def get_atm_strike(df, spot):
    try:
        return int(df.iloc[(df["Strike"] - spot).abs().argsort()[:1]]["Strike"].values[0])
    except:
        return 0


# Highlight
def highlight_atm(row, atm):
    if row["Strike"] == atm:
        return ["background-color: #00FFAA"] * len(row)
    return [""] * len(row)
