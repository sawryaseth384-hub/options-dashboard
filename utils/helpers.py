import pandas as pd

def process_option_data(data):

    rows = []

    for item in data:
        strike = item["strikePrice"]

        ce = item.get("CE", {})
        pe = item.get("PE", {})

        rows.append({
            "Strike": strike,

            "Call OI": ce.get("openInterest", 0),
            "Call LTP": ce.get("lastPrice", 0),
            "Call IV": ce.get("impliedVolatility", 0),

            "Put OI": pe.get("openInterest", 0),
            "Put LTP": pe.get("lastPrice", 0),
            "Put IV": pe.get("impliedVolatility", 0),
        })

    df = pd.DataFrame(rows)

    df["PCR"] = df["Put OI"] / df["Call OI"].replace(0, 1)

    return df
