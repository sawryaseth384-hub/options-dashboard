def get_stock_df():
    df = load_instruments()

    # 🔥 ONLY F&O
    df = df[df["SEM_SEGMENT"] == "D"]

    df = df[[
        "SEM_TRADING_SYMBOL",
        "SEM_SMST_SECURITY_ID",
        "SEM_SEGMENT"
    ]]

    return df


def get_index_df():
    import pandas as pd

    data = [
        {"SEM_TRADING_SYMBOL": "NIFTY", "SEM_SMST_SECURITY_ID": 13, "SEM_SEGMENT": "I"},
        {"SEM_TRADING_SYMBOL": "BANKNIFTY", "SEM_SMST_SECURITY_ID": 25, "SEM_SEGMENT": "I"},
        {"SEM_TRADING_SYMBOL": "FINNIFTY", "SEM_SMST_SECURITY_ID": 27, "SEM_SEGMENT": "I"},
    ]

    return pd.DataFrame(data)


def get_instrument_df():
    return pd.concat([get_stock_df(), get_index_df()], ignore_index=True)
