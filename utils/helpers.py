import pandas as pd

def process_option_data(raw_data):
    try:
        data = raw_data.get("data", {})
        spot = data.get("last_price", 0)

        oc = data.get("oc", {})

        rows = []

        for strike, values in oc.items():
            ce = values.get("ce", {})
            pe = values.get("pe", {})

            rows.append({
                "Strike": float(strike),

                "CE OI": ce.get("oi", 0),
                "CE LTP": ce.get("last_price", 0),
                "CE Delta": ce.get("greeks", {}).get("delta", 0),

                "PE OI": pe.get("oi", 0),
                "PE LTP": pe.get("last_price", 0),
                "PE Delta": pe.get("greeks", {}).get("delta", 0),
            })

        df = pd.DataFrame(rows)

        return df.sort_values("Strike"), spot

    except Exception:
        return pd.DataFrame(), 0
