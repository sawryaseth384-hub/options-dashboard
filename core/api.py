import os
import time
import pandas as pd
import numpy as np
from dhanhq import dhanhq

DHAN_CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN")

NIFTY_SECURITY_ID = "13"
EXCHANGE_SEGMENT = "IDX_I"

if DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN:
    dhan = dhanhq(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
else:
    dhan = None


def fetch_data():
    """Header + basic data"""
    return {
        "NIFTY": {"ltp": 23700, "change": 120},
        "BANKNIFTY": {"ltp": 55200, "change": 300},
        "SENSEX": {"ltp": 78500, "change": 250},
        "VIX": {"ltp": 18.2, "change": -0.5},
        "DOW": {"ltp": 38000, "change": 200},
        "NASDAQ": {"ltp": 16500, "change": -50},
        "GIFT": {"ltp": 23750, "change": 80},
        "CRUDE": {"ltp": 6500, "change": 30},
        "GOLD": {"ltp": 72000, "change": 100},
        "SILVER": {"ltp": 85000, "change": 200},
        "USDINR": {"ltp": 83.1, "change": 0.1},
        "DXY": {"ltp": 104.2, "change": -0.2},
    }


def get_option_chain():
    """Simple sample (later real API connect करेंगे)"""
    strikes = np.arange(22000, 22500, 50)

    data = []
    for s in strikes:
        data.append({
            "Strike": s,
            "Call OI": np.random.randint(50000, 200000),
            "Put OI": np.random.randint(50000, 200000),
        })

    return pd.DataFrame(data)
