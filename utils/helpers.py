import pandas as pd


# =========================
# 🔥 PROCESS OPTION DATA
# =========================
def process_option_data(raw_data):
    try:
        data = raw_data.get("data", {})
        spot = data.get("last_price", 0)

        oc = data.get("oc", {})
        rows = []

        for strike, value in oc.items():

            strike_val = float(strike)

            # 🔥 FILTER NEAR ATM (+/-1000)
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

        # 🔥 SAFETY
        if df.empty:
            return df, spot

        df = df.sort_values("Strike").reset_index(drop=True)

        return df, spot

    except Exception as e:
        print("PROCESS ERROR:", e)
        return pd.DataFrame(), 0


# =========================
# 📊 PCR (Put Call Ratio)
# =========================
def calculate_pcr(df):
    try:
        total_ce_oi = df["CE OI"].sum()
        total_pe_oi = df["PE OI"].sum()

        if total_ce_oi == 0:
            return 0

        return round(total_pe_oi / total_ce_oi, 2)

    except Exception as e:
        print("PCR Error:", e)
        return 0


# =========================
# 🟢 SUPPORT / 🔴 RESISTANCE
# =========================
def get_support_resistance(df):
    try:
        support = df.loc[df["PE OI"].idxmax(), "Strike"]
        resistance = df.loc[df["CE OI"].idxmax(), "Strike"]

        return int(support), int(resistance)

    except Exception as e:
        print("SR Error:", e)
        return 0, 0


# =========================
# 🚀 MARKET SIGNAL
# =========================
def get_signal(pcr):
    try:
        if pcr > 1.2:
            return "📈 Bullish"
        elif pcr < 0.8:
            return "📉 Bearish"
        else:
            return "⚖️ Sideways"

    except:
        return "N/A"


# =========================
# 🎯 ATM STRIKE
# =========================
def get_atm_strike(df, spot):
    try:
        df_copy = df.copy()  # 🔥 safe copy (important)
        df_copy["diff"] = abs(df_copy["Strike"] - spot)

        atm_row = df_copy.loc[df_copy["diff"].idxmin()]

        return int(atm_row["Strike"])

    except Exception as e:
        print("ATM Error:", e)
        return 0
