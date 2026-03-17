import requests
from utils.config import ACCESS_TOKEN, CLIENT_ID

class MarketQuote:

    def __init__(self):
        self.url = "https://api.dhan.co/v2/marketfeed/quote"   # ✅ CORRECT

    def get_data(self, instruments):

        headers = {
            "access-token": ACCESS_TOKEN,
            "client-id": CLIENT_ID,
            "Content-Type": "application/json"
        }

        payload = instruments

        try:
            res = requests.post(self.url, headers=headers, json=payload)
            return res.json()

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
