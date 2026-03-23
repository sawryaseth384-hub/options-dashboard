import requests
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

def get_option_chain(security_id, expiry):

    # ✅ CORRECT ENDPOINT
    url = f"{BASE_URL}/optionchain"

    headers = get_headers()

    payload = {
        "UnderlyingScrip": security_id,
        "UnderlyingSeg": "IDX_I",
        "Expiry": expiry
    }

    try:
        res = requests.post(url, headers=headers, json=payload)

        # 🔥 DEBUG
        print("STATUS:", res.status_code)
        print("RAW:", res.text)

        try:
            return res.json()
        except:
            return {"error": res.text}

    except Exception as e:
        return {"error": str(e)}
