import requests
import pandas as pd
from utils.config import ACCESS_TOKEN, CLIENT_ID

BASE_URL = "https://api.dhan.co/v2"


class HistoricalData:

    def __init__(self):
        self.headers = {
            "access-token": ACCESS_TOKEN,
            "client-id": CLIENT_ID,
            "Content-Type": "application/json"
        }

    # 🔥 COMMON REQUEST
    def _post(self, endpoint, payload):
        try:
            url = f"{BASE_URL}{endpoint}"
            response = requests.post(url, headers=self.headers, json=payload)

            data = response.json()

            return data

        except Exception as e:
            return {"status": "error", "message": str(e)}

    # 🔹 DAILY DATA
    def get_daily_data(self, security_id, segment="NSE_EQ"):
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": segment,
            "instrument": "EQUITY",
            "expiryCode": 0,
            "oi": False,
            "fromDate": "2023-01-01",
            "toDate": "2024-01-01"
        }

        data = self._post("/charts/historical", payload)

        return self._convert_to_df(data)

    # 🔹 INTRADAY DATA
    def get_intraday_data(self, security_id, segment="NSE_EQ"):
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": segment,
            "instrument": "EQUITY",
            "interval": "5",  # 1,5,15,25,60
            "oi": False,
            "fromDate": "2024-03-01 09:15:00",
            "toDate": "2024-03-10 15:30:00"
        }

        data = self._post("/charts/intraday", payload)

        return self._convert_to_df(data)

    # 🔥 CONVERT TO DATAFRAME
    def _convert_to_df(self, data):
        try:
            df = pd.DataFrame({
                "open": data.get("open", []),
                "high": data.get("high", []),
                "low": data.get("low", []),
                "close": data.get("close", []),
                "volume": data.get("volume", []),
                "timestamp": data.get("timestamp", [])
            })

            if df.empty:
                return df

            # Convert timestamp
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

            return df

        except Exception as e:
            print("DF Error:", e)
            return pd.DataFrame()
