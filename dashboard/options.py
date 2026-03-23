import requests
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

def get_option_chain(security_id, expiry):

    url = f"{BASE_URL}/optionchain/optionchain"
    headers = get_headers()

    payload = {
        "UnderlyingScrip": security_id,
        "UnderlyingSeg": "IDX_I",
        "Expiry": expiry
    }

    try:
        res = requests.post(url, headers=headers, json=payload)

        # ✅ DEBUG (IMPORTANT)
        print("STATUS:", res.status_code)
        print("RAW RESPONSE:", res.text)

        # ✅ SAFE JSON PARSE
        try:
            data = res.json()
        except:
            return {"error": res.text}

        return data

    except Exception as e:
        return {"error": str(e)}
