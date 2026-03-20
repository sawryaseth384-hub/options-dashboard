import requests
from utils.config import ACCESS_TOKEN, CLIENT_ID


class MarketQuote:

    def __init__(self):
        self.url = "https://api.dhan.co/v2/marketfeed/quote"

    def get_data(self, instruments):

        headers = {
            "access-token": ACCESS_TOKEN,
            "client-id": CLIENT_ID,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            res = requests.post(self.url, headers=headers, json=instruments)

            if res.status_code != 200:
                return {"error": f"HTTP {res.status_code}", "msg": res.text}

            data = res.json()

            if data.get("status") != "success":
                return {"error": "API Failed", "msg": data}

            return data

        except Exception as e:
            return {"error": str(e)}
