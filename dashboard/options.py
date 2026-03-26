from dhan_data.client import safe_post

BASE_URL = "https://api.dhan.co"

def get_option_chain(security_id, expiry):

    url = f"{BASE_URL}/v2/optionchain"
    payload = {
        "UnderlyingScrip": security_id,
        "UnderlyingSeg": "NSE_FNO",
        "Expiry": expiry
    }

    try:
        data, err = safe_post(url, payload)
        if err:
            return {"_error": err}
        return data

    except Exception as e:
        return {"_error": str(e)}
