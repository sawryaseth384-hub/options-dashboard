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
        # ✅ IMPORTANT CHANGE (json= NOT data=)
        res = requests.post(url, headers=headers, json=payload)

        # Debug print
        print("Status:", res.status_code)
        print("Response:", res.text)

        if res.status_code == 200:
            return res.json()
        else:
            return {"error": res.text}

    except Exception as e:
        return {"error": str(e)}
