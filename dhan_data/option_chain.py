import requests
from core.token_manager import get_headers

URL = "https://api.dhan.co/v2/optionchain"

def get_option_chain(security_id, expiry):

    headers = get_headers()

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": "IDX_I",
        "Expiry": expiry   # 🔥 string hi rehne do
    }

    try:
        response = requests.post(
            URL,
            headers=headers,
            json=payload,
            timeout=10
        )

        data = response.json()

        # 🔥 DEBUG (Streamlit me dikhao)
        return {
            "status_code": response.status_code,
            "data": data
        }

    except Exception as e:
        return {"error": str(e)}
