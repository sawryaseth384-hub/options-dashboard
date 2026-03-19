import pandas as pd

def process_option_data(response):
    if not response or "data" not in response:
        return pd.DataFrame(), 0

    data = response["data"]

    spot = data.get("last_price", 0)
    oc = data.get("oc", {})

    rows = []

    for strike, val in oc.items():
        ce = val.get("ce", {})
        pe = val.get("pe", {})

        rows.append({
            "Strike": float(strike),

            "Call OI": ce.get("oi", 0),
            "Call LTP": ce.get("last_price", 0),
            "Call IV": ce.get("implied_volatility", 0),

            "Put OI": pe.get("oi", 0),
            "Put LTP": pe.get("last_price", 0),
            "Put IV": pe.get("implied_volatility", 0),
        })

    df = pd.DataFrame(rows).sort_values("Strike")

    return df, spot
