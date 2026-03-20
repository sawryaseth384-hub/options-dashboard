import pandas as pd

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

        # 🔥 SAFETY CHECK
        if df.empty:
            return df, spot

        # 🔥 SORT SAFE
        df = df.sort_values("Strike").reset_index(drop=True)

        return df, spot

    except Exception as e:
        print("PROCESS ERROR:", e)
        return pd.DataFrame(), 0
