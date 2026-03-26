import requests
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co"
url = f"{BASE_URL}/v2/charts/intraday"
payload = {
    "securityId": "13",                 # NIFTY
    "exchangeSegment": "IDX_I",         # IDX_I for indices
    "instrument": "INDEX",              # INDEX for NIFTY, EQUITY for stocks
    "interval": "5",                    # 5 minute candles
    "oi": False,
    "fromDate": "2026-03-23 09:15:00",
    "toDate": "2026-03-24 15:30:00"
}
res = requests.post(url, headers=get_headers(), json=payload)
print("Status:", res.status_code)
if res.status_code == 401:
    print("Response:", {"_error": "Unauthorized - check token"})
else:
    print("Response:", res.json())
