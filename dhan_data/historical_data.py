import requests
import time
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

# =========================
# 🔥 HARDCORE HISTORICAL
# =========================
def get_historical(security_id, segment, retries=3):
    """
    Robust historical fetch:
    - retry system
    - fallback handling
    - always returns structured data
    """

    payload = {
        "securityId": str(security_id),
        "exchangeSegment": segment,
        "interval": "1",   # 1 minute
        "fromDate": "2025-03-25",
        "toDate": "2025-03-25"
    }

    for attempt in range(retries):
        try:
            print(f"\n🔁 Attempt {attempt+1}")

            res = requests.post(
                f"{BASE_URL}/charts/historical",
                headers=get_headers(),
                json=payload,
                timeout=10
            )

            print("Status:", res.status_code)

            if res.status_code != 200:
                print("❌ Bad Status")
                time.sleep(1)
                continue

            data = res.json()

            if "data" not in data:
                print("❌ No 'data' key")
                time.sleep(1)
                continue

            final = data["data"]

            # 🔴 VALIDATION
            if not final or len(final.get("close", [])) < 2:
                print("⚠️ Not enough candles")
                time.sleep(1)
                continue

            print("✅ HISTORICAL SUCCESS")
            return final

        except Exception as e:
            print("❌ ERROR:", e)
            time.sleep(1)

    # =========================
    # 🔥 FALLBACK SYSTEM
    # =========================
    print("🚨 FALLBACK ACTIVATED")

    return {
        "open": [],
        "high": [],
        "low": [],
        "close": [],
        "timestamp": []
    }
