import requests
from utils.config import ACCESS_TOKEN, CLIENT_ID

BASE_URL = "https://api.dhan.co/v2"


class MarketQuote:

    def __init__(self):
        self.headers = {
            "access-token": ACCESS_TOKEN,
            "client-id": CLIENT_ID,
            "Content-Type": "application/json"
        }

    def _post(self, endpoint, payload):
        try:
            url = f"{BASE_URL}{endpoint}"
            response = requests.post(url, headers=self.headers, json=payload)

            data = response.json()

            if data.get("status") != "success":
                print("API Error:", data)

            return data

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_quote(self, instruments):
        return self._post("/marketfeed/quote", instruments)
