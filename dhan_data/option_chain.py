def get_option_chain(sec, expiry):
    payload = {
        "UnderlyingScrip": int(sec),
        "UnderlyingSeg": "IDX_I",
        "expiryDate": expiry   # ✅ FIXED
    }

    data, err = safe_post("https://api.dhan.co/v2/optionchain", payload)

    if err:
        return None, err

    if not data or data.get("status") != "success":
        return None, data

    # ✅ handle both formats
    if "oc" in data["data"]:
        return data["data"]["oc"], None
    elif "records" in data["data"]:
        return data["data"]["records"], None

    return None, "Parse Error"
