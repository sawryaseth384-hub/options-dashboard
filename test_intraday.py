import requests
from core.token_manager import get_headers

url = "https://api.dhan.co/v2/charts/intraday"
payload = {
    "securityId": "13",                 # NIFTY
    "exchangeSegment": "NSE_EQ",        # Always NSE_EQ for charts
    "instrument": "INDEX",              # INDEX for NIFTY, EQUITY for stocks
    "interval": "5",                    # 5 minute candles
    "oi": False,
    "fromDate": "2026-03-23 09:15:00",
    "toDate": "2026-03-24 15:30:00"
}
res = requests.post(url, headers=get_headers(), json=payload)
print("Status:", res.status_code)
print("Response:", res.json())
