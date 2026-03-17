import requests
from utils.config import DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID

# 🔹 Common headers
def get_headers():
    return {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": str(DHAN_CLIENT_ID),
        "Content-Type": "application/json"
    }

# 🔹 Step 1: Expiry List
def get_expiry_list():

    url = "https://api.dhan.co/v2/optionchain/expirylist"

    payload = {
        "UnderlyingScrip": 13,
        "UnderlyingSeg": "IDX_I"
    }

    response = requests.post(url, headers=get_headers(), json=payload)

    return response.json()

# 🔹 Step 2: Option Chain (Auto latest expiry)
def get_option_chain():

    expiry_data = get_expiry_list()

    # safety check
    if "data" not in expiry_data:
        return expiry_data

    expiry_list = expiry_data["data"]

    if not expiry_list:
        return {"error": "No expiry found"}

    nearest_expiry = expiry_list[0]   # 🔥 first expiry

    url = "https://api.dhan.co/v2/optionchain"

    payload = {
        "UnderlyingScrip": 13,
        "UnderlyingSeg": "IDX_I",
        "Expiry": nearest_expiry
    }

    response = requests.post(url, headers=get_headers(), json=payload)

    return response.json()
