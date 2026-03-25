import requests
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

def get_historical(security_id, segment):
    try:
        print("\n========== HISTORICAL DEBUG START ==========")
        print("Security ID:", security_id)
        print("Segment:", segment)

        payload = {
            "securityId": str(security_id),
            "exchangeSegment": segment,
            "instrument": "EQUITY",
            "interval": "1",   # 1 minute
            "fromDate": "2025-03-20",
            "toDate": "2025-03-25"
        }

        print("Payload:", payload)

        res = requests.post(
            f"{BASE_URL}/charts/intraday",
            headers=get_headers(),
            json=payload
        )

        print("Status Code:", res.status_code)
        print("Raw Response:", res.text)

        if res.status_code != 200:
            print("❌ API FAILED")
            return {}

        data = res.json()

        print("Parsed JSON:", data)

        final_data = data.get("data", {})

        if not final_data:
            print("❌ EMPTY DATA RECEIVED")
        else:
            print("✅ DATA RECEIVED KEYS:", final_data.keys())
            print("Sample Close:", final_data.get("close", [])[:5])

        print("========== HISTORICAL DEBUG END ==========\n")

        return final_data

    except Exception as e:
        print("❌ HISTORICAL ERROR:", e)
        return {}
