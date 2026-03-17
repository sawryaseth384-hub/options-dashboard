import requests
from utils.config import ACCESS_TOKEN, CLIENT_ID


class OptionChain:

    def __init__(self):
        self.base_url = "https://api.dhan.co/v2"

    # 🔹 GET EXPIRY LIST
    def get_expiry_list(self):
        url = f"{self.base_url}/optionchain/expirylist"

        headers = {
            "access-token": ACCESS_TOKEN,
            "client-id": CLIENT_ID,
            "Content-Type": "application/json"
        }

        payload = {
            "UnderlyingScrip": 13,
            "UnderlyingSeg": "IDX_I"
        }

        try:
            res = requests.post(url, headers=headers, json=payload)
            data = res.json()

            if data.get("status") == "success":
                return data.get("data", [])
            else:
                return []

        except Exception as e:
            return []

    # 🔹 GET OPTION CHAIN (WITH EXPIRY)
    def get_data(self):

        expiry_list = self.get_expiry_list()

        if not expiry_list:
            return {"error": "No expiry data"}

        # 🔥 nearest expiry auto select
        expiry = expiry_list[0]

        url = f"{self.base_url}/optionchain"

        headers = {
            "access-token": ACCESS_TOKEN,
            "client-id": CLIENT_ID,
            "Content-Type": "application/json"
        }

        payload = {
            "UnderlyingScrip": 13,
            "UnderlyingSeg": "IDX_I",
            "Expiry": expiry
        }

        try:
            res = requests.post(url, headers=headers, json=payload)
            data = res.json()

            return {
                "expiry": expiry,
                "data": data
            }

        except Exception as e:
            return {"error": str(e)}
