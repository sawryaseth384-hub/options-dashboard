import pandas as pd

def process_option_data(raw_data):
    try:
        data = raw_data.get("data", {})
        spot = data.get("last_price", 0)

        oc = data.get("oc", {})

        rows = []

        for strike, value in oc.items():

            ce = value.get("ce", {})
            pe = value.get("pe", {})

            rows.append({
                "Strike": int(float(strike)),

                "CE OI": ce.get("oi", 0),
                "CE LTP": ce.get("last_price", 0),
                "CE Delta": ce.get("greeks", {}).get("delta", 0),

                "PE OI": pe.get("oi", 0),
                "PE LTP": pe.get("last_price", 0),
                "PE Delta": pe.get("greeks", {}).get("delta", 0),
            })

        df = pd.DataFrame(rows)

        return df.sort_values("Strike"), spot

    except Exception as e:
        print("Error:", e)
        return pd.DataFrame(), 0
