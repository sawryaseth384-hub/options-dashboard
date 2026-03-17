import pandas as pd

def get_instrument_list():

    url = "https://images.dhan.co/api-data/api-scrip-master.csv"

    try:
        df = pd.read_csv(url)

        # सही column names (FIXED)
        df = df[[
            "SEM_EXM_EXCH_ID",
            "SEM_SEGMENT",
            "SEM_TRADING_SYMBOL",
            "SEM_CUSTOM_SYMBOL",   # ✅ FIXED
            "SEM_EXPIRY_DATE",
            "SEM_STRIKE_PRICE",
            "SEM_OPTION_TYPE"
        ]]

        return df.head(20).to_dict(orient="records")

    except Exception as e:
        return {"error": str(e)}
