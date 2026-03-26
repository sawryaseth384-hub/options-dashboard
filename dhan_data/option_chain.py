from dhan_data.client import safe_post

BASE_URL = "https://api.dhan.co"


def get_option_chain(sec, expiry, segment="IDX_I"):
    payload = {
        "UnderlyingScrip": int(sec),
        "UnderlyingSeg": segment,
        "expiryDate": expiry
    }

    data, err = safe_post(f"{BASE_URL}/v2/optionchain", payload)
    if err:
        return None, err
    if not data or data.get("status") not in (None, "success"):
        return None, data

    payload_data = data.get("data") if isinstance(data, dict) else None
    if not payload_data:
        return None, "No data"

    if "oc" in payload_data:
        return payload_data.get("oc"), None
    if "records" in payload_data:
        return payload_data.get("records"), None

    return None, "Parse Error"
