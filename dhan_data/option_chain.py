import requests
import streamlit as st
from core.token_manager import get_headers

URL = "https://api.dhan.co/v2/optionchain"

def get_option_chain(security_id, expiry, segment="IDX_I"):
    try:
        if not security_id:
            raise ValueError("Security ID missing")

        security_id = int(security_id)

        if not expiry:
            raise ValueError("Expiry missing")

        headers = get_headers()

        payload = {
            "UnderlyingScrip": security_id,
            "UnderlyingSeg": segment,
            "expiryDate": expiry   # ✅ FIXED
        }

        response = requests.post(URL, headers=headers, json=payload, timeout=10)

        if response.status_code != 200:
            st.error(f"HTTP Error: {response.status_code}")
            st.write(response.text)
            return {"error": "HTTP Error"}

        data = response.json()

        # 🔥 Debug print (temporary)
        # st.write(data)

        if data.get("status") != "success":
            return {"error": data}

        return data["data"]["oc"]   # ✅ correct extraction

    except Exception as e:
        st.error(f"Option chain error: {e}")
        return {"error": str(e)}
