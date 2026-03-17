import requests
import pandas as pd
from utils.config import DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID

BASE_URL = "https://api.dhan.co/v2"


# 🔥 1. GET EXPIRY LIST
def get_expiry_list(security_id=13):
    url = f"{BASE_URL}/optionchain/expirylist"

    headers = {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
        "Content-Type": "application/json"
    }

    payload = {
        "UnderlyingScrip": security_id,
        "UnderlyingSeg": "IDX_I"
    }

    res = requests.post(url, headers=headers, json=payload).json()

    return res.get("data", [])


# 🔥 2. GET OPTION CHAIN (AUTO EXPIRY)
def get_option_chain(security_id=13):

    headers = {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
        "Content-Type": "application/json"
    }

    # 👉 AUTO EXPIRY
    expiries = get_expiry_list(security_id)

    if not expiries:
        return pd.DataFrame({"error": ["No expiry found"]})

    expiry = expiries[0]  # nearest expiry

    url = f"{BASE_URL}/optionchain"

    payload = {
        "UnderlyingScrip": security_id,
        "UnderlyingSeg": "IDX_I",
        "Expiry": expiry
    }

    try:
        data = requests.post(url, headers=headers, json=payload).json()

        oc = data.get("data", {}).get("oc", {})

        rows = []

        for strike, values in oc.items():

            ce = values.get("ce", {})
            pe = values.get("pe", {})

            rows.append({
                "strike": float(strike),

                "ce_ltp": ce.get("last_price", 0),
                "ce_oi": ce.get("oi", 0),
                "ce_volume": ce.get("volume", 0),

                "pe_ltp": pe.get("last_price", 0),
                "pe_oi": pe.get("oi", 0),
                "pe_volume": pe.get("volume", 0),
            })

        df = pd.DataFrame(rows).sort_values("strike")

        return df

    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})
