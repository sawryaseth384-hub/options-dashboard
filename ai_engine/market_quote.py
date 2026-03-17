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

    # 🔹 COMMON REQUEST HANDLER
    def _post(self, endpoint, payload):
        try:
            url = f"{BASE_URL}{endpoint}"
            response = requests.post(url, headers=self.headers, json=payload)

            if response.status_code != 200:
                return {"status": "error", "message": response.text}

            data = response.json()

            if data.get("status") != "success":
                return {"status": "error", "message": data}

            return data

        except Exception as e:
            return {"status": "error", "message": str(e)}

    # 🔥 1. LTP DATA
    def get_ltp(self, instruments):
        """
        instruments example:
        {
            "NSE_EQ": [11536],
            "NSE_FNO": [49081]
        }
        """
        return self._post("/marketfeed/ltp", instruments)

    # 🔥 2. OHLC DATA
    def get_ohlc(self, instruments):
        return self._post("/marketfeed/ohlc", instruments)

    # 🔥 3. FULL MARKET DATA (MOST IMPORTANT)
    def get_quote(self, instruments):
        return self._post("/marketfeed/quote", instruments)
