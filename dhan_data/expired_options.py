import requests
import pandas as pd
from utils.config import ACCESS_TOKEN, CLIENT_ID

BASE_URL = "https://api.dhan.co/v2"


class ExpiredOptionsData:

    def __init__(self):
        self.headers = {
            "access-token": ACCESS_TOKEN,
            "client-id": CLIENT_ID,
            "Content-Type": "application/json"
        }

    # 🔥 MAIN FUNCTION
    def get_data(
        self,
        security_id,
        option_type="CALL",   # CALL / PUT
        strike="ATM",         # ATM / ATM+1 / ATM-1
        interval="1"          # 1,5,15,60
    ):

        payload = {
            "exchangeSegment": "NSE_FNO",
            "interval": interval,
            "securityId": security_id,
            "instrument": "OPTIDX",
            "expiryFlag": "WEEK",
            "expiryCode": 0,
            "strike": strike,
            "drvOptionType": option_type,
            "requiredData": [
                "open",
                "high",
                "low",
                "close",
                "volume",
                "oi",
                "iv",
                "spot",
                "strike"
            ],
            "fromDate": "2024-01-01",
            "toDate": "2024-02-01"
        }

        try:
            url = f"{BASE_URL}/charts/rollingoption"

            response = requests.post(url, headers=self.headers, json=payload)
            data = response.json()

            return self._convert_to_df(data, option_type)

        except Exception as e:
            print("Error:", e)
            return pd.DataFrame()

    # 🔥 CONVERT TO DATAFRAME
    def _convert_to_df(self, data, option_type):
        try:
            key = "ce" if option_type == "CALL" else "pe"

            option_data = data.get("data", {}).get(key, {})

            if not option_data:
                return pd.DataFrame()

            df = pd.DataFrame({
                "open": option_data.get("open", []),
                "high": option_data.get("high", []),
                "low": option_data.get("low", []),
                "close": option_data.get("close", []),
                "volume": option_data.get("volume", []),
                "oi": option_data.get("oi", []),
                "iv": option_data.get("iv", []),
                "spot": option_data.get("spot", []),
                "strike": option_data.get("strike", []),
                "timestamp": option_data.get("timestamp", [])
            })

            if df.empty:
                return df

            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

            return df

        except Exception as e:
            print("DF Error:", e)
            return pd.DataFrame()
