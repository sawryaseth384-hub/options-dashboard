import requests
import streamlit as st
from core.token_manager import get_headers

URL = "https://api.dhan.co/v2/optionchain"

def get_option_chain(security_id, expiry, segment="IDX_I"):
    """
    Fetch option chain data from Dhan API.
    - security_id: int or str convertible to int
    - expiry: string in YYYY-MM-DD format
    - segment: "IDX_I" for indices, "NSE_FNO" for stocks/futures (optional, default IDX_I)
    Returns: dict with "data" key containing the API response, or empty dict on failure.
    """
    try:
        # Validate inputs
        if security_id is None or security_id == "":
            raise ValueError("Security ID missing")
        try:
            security_id = int(security_id)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid security ID: {security_id}")

        if not expiry:
            raise ValueError("Expiry missing")
        # optional: check expiry format
        if not isinstance(expiry, str) or len(expiry.split("-")) != 3:
            raise ValueError(f"Invalid expiry format: {expiry}")

        headers = get_headers()
        headers["Content-Type"] = "application/json"

        payload = {
            "UnderlyingScrip": security_id,
            "UnderlyingSeg": segment,
            "Expiry": expiry
        }

        response = requests.post(URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()

        data = response.json()

        if "errorCode" in data:
            st.error(f"API Error: {data.get('errorCode')} - {data.get('errorMessage')}")
            return {"error": data.get("errorMessage")}
        return data

    except Exception as e:
        st.error(f"Option chain error: {e}")
        return {"error": str(e)}
