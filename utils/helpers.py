import pandas as pd

def process_option_data(api_response):
    if not api_response or "data" not in api_response:
        return pd.DataFrame(), 0

    data = api_response["data"]

    # 🔥 Spot price
    spot_price = data.get("last_price", 0)

    # 🔥 Option chain object
    oc_data = data.get("oc", {})

    rows = []

    for strike_str, option in oc_data.items():
        try:
            strike = float(strike_str)

            ce = option.get("ce", {})
            pe = option.get("pe", {})

            rows.append({
                "Strike": strike,

                # CALL
                "Call OI": ce.get("oi", 0),
                "Call LTP": ce.get("last_price", 0),
                "Call IV": ce.get("implied_volatility", 0),
                "Call Delta": ce.get("greeks", {}).get("delta", 0),
                "Call Gamma": ce.get("greeks", {}).get("gamma", 0),
                "Call Theta": ce.get("greeks", {}).get("theta", 0),
                "Call Vega": ce.get("greeks", {}).get("vega", 0),

                # PUT
                "Put OI": pe.get("oi", 0),
                "Put LTP": pe.get("last_price", 0),
                "Put IV": pe.get("implied_volatility", 0),
                "Put Delta": pe.get("greeks", {}).get("delta", 0),
                "Put Gamma": pe.get("greeks", {}).get("gamma", 0),
                "Put Theta": pe.get("greeks", {}).get("theta", 0),
                "Put Vega": pe.get("greeks", {}).get("vega", 0),
            })

        except Exception:
            continue

    df = pd.DataFrame(rows)

    if df.empty:
        return df, spot_price

    df = df.sort_values("Strike").reset_index(drop=True)

    # 🔥 Extra metrics
    df["Total OI"] = df["Call OI"] + df["Put OI"]
    df["PCR"] = df["Put OI"] / df["Call OI"].replace(0, 1)

    return df, spot_price
