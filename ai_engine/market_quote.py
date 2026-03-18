import requests
from utils.config import ACCESS_TOKEN, CLIENT_ID

class MarketQuote:

    def __init__(self):
        self.url = "https://api.dhan.co/v2/marketfeed/quote"

    def get_data(self, instruments):

        # 🔥 FORCE INT FIX
        for key in instruments:
            instruments[key] = [int(x) for x in instruments[key]]

        headers = {
            "access-token": ACCESS_TOKEN,
            "client-id": CLIENT_ID,
            "Content-Type": "application/json"
        }

        try:
            print("TOKEN LENGTH:", len(ACCESS_TOKEN) if ACCESS_TOKEN else 0)
            print("CLIENT:", CLIENT_ID)
            print("PAYLOAD:", instruments)

            res = requests.post(self.url, headers=headers, json=instruments)

            data = res.json()

            print("RESPONSE:", data)

            # 🔥 ERROR HANDLE
            if data.get("status") != "success":
                return {
                    "status": "error",
                    "api_error": data
                }

            return data

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
