import requests
from utils.config import ACCESS_TOKEN, CLIENT_ID

class MarketQuote:
import requests
from utils.config import ACCESS_TOKEN, CLIENT_ID

class MarketQuote:

    def __init__(self):
        self.url = "https://api.dhan.co/v2/marketfeed/quote"

    def get_data(self, instruments):

        # ✅ Ensure int values
        for key in instruments:
            instruments[key] = [int(x) for x in instruments[key]]

        headers = {
            "access-token": ACCESS_TOKEN,
            "client-id": CLIENT_ID,
            "Content-Type": "application/json"
        }

        try:
            print("\n===== DEBUG START =====")
            print("TOKEN LENGTH:", len(ACCESS_TOKEN) if ACCESS_TOKEN else 0)
            print("CLIENT ID:", CLIENT_ID)
            print("PAYLOAD:", instruments)

            res = requests.post(self.url, headers=headers, json=instruments)

            print("STATUS CODE:", res.status_code)

            try:
                data = res.json()
            except:
                return {
                    "status": "error",
                    "message": "Invalid JSON response",
                    "raw": res.text
                }

            print("RESPONSE:", data)
            print("===== DEBUG END =====\n")

            # ✅ API error handling
            if res.status_code != 200:
                return {
                    "status": "error",
                    "http_error": res.status_code,
                    "response": data
                }

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
