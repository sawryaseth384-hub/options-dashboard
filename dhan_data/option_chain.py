def get_option_chain(security_id, expiry, segment="IDX_I"):
    try:
        headers = get_headers()

        payload = {
            "UnderlyingScrip": int(security_id),
            "UnderlyingSeg": segment,
            "expiryDate": expiry   # ✅ correct
        }

        res = requests.post(URL, headers=headers, json=payload, timeout=10)

        if res.status_code != 200:
            return None, f"HTTP {res.status_code}"

        data = res.json()

        # 🔥 DEBUG (important)
        # st.write(data)

        if data.get("status") != "success":
            return None, data

        # ✅ HANDLE BOTH STRUCTURES
        if "oc" in data["data"]:
            return data["data"]["oc"], None

        elif "records" in data["data"]:
            return data["data"]["records"], None

        else:
            return None, "Unknown structure"

    except Exception as e:
        return None, str(e)
