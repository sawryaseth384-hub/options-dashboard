import requests
import streamlit as st
from core.token_manager import get_headers

URL = "https://api.dhan.co/v2/optionchain"

def get_option_chain(security_id, expiry):
    """
    Fetch option chain data from Dhan API.
    """
    try:
        # Validate inputs
        if security_id is None or security_id == "":
            raise ValueError("Security ID cannot be empty or None")

        # Convert to int safely
        try:
            security_id = int(security_id)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid security ID: {security_id}. Must be convertible to integer.")

        if not isinstance(expiry, str) or len(expiry.split("-")) != 3:
            raise ValueError(f"Invalid expiry format: {expiry}. Expected YYYY-MM-DD.")

        headers = get_headers()
        headers["Content-Type"] = "application/json"

        payload = {
            "UnderlyingScrip": security_id,
            "UnderlyingSeg": "IDX_I",   # Adjust if needed for stocks
            "Expiry": expiry
        }

        response = requests.post(URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()

        data = response.json()

        if "errorCode" in data:
            error_msg = f"API Error: {data.get('errorCode')} - {data.get('errorMessage')}"
            st.error(error_msg)
            return {"error": error_msg}

        return data

    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {e}")
        return {"error": str(e)}
    except Exception as e:
        st.error(f"Error fetching option chain: {e}")
        return {"error": str(e)}
