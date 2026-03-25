import requests

from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"


def get_option_chain(security_id, expiry, segment="IDX_I"):
    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment,
        "Expiry": expiry,
    }

    try:
        res = requests.post(
            f"{BASE_URL}/optionchain",
            headers=get_headers(),
            json=payload,
            timeout=10,
        )
        if res.status_code != 200:
            return None, res.text
        data = res.json()
    except Exception as exc:
        return None, str(exc)

    if not data or data.get("status") != "success":
        return None, data

    chain = data.get("data", {}).get("oc") or data.get("data", {}).get("records")
    if not chain:
        return None, "Parse Error"

    return data, None
