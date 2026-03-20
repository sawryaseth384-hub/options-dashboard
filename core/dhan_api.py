def get_expiry_list(security_id, segment):
    url = f"{BASE_URL}/optionchain/expirylist"

    payload = {
        "UnderlyingScrip": security_id,
        "UnderlyingSeg": segment
    }

    res = requests.post(url, headers=get_headers(), json=payload)
    data = res.json()

    return data.get("data", [])


def get_valid_expiries(security_id, segment):
    # 🔥 NO FILTER (ALL expiry)
    return get_expiry_list(security_id, segment)


def get_option_chain(security_id, segment, expiry):
    url = f"{BASE_URL}/optionchain"

    payload = {
        "UnderlyingScrip": security_id,
        "UnderlyingSeg": segment,
        "Expiry": expiry
    }

    res = requests.post(url, headers=get_headers(), json=payload)
    return res.json()
