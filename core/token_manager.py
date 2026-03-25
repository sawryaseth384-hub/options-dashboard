# core/token_manager.py
import time
import streamlit as st
from datetime import datetime
from dhanhq import dhanhq

def get_token():
    """Get a valid token, refreshing if necessary."""
    # Initialize session state if needed
    if "token" not in st.session_state:
        st.session_state.token = None
        st.session_state.expiry = 0

    # If we have a token, check its expiry (handles both string and numeric)
    if st.session_state.token:
        expiry = st.session_state.expiry
        # Convert string expiry to numeric if needed
        if isinstance(expiry, str):
            try:
                # Try to parse ISO format like "2026-03-25T17:10:37Z"
                if expiry.endswith('Z'):
                    expiry = expiry.replace('Z', '+00:00')
                dt = datetime.fromisoformat(expiry)
                expiry = dt.timestamp()
                # Update session state to numeric for future runs
                st.session_state.expiry = expiry
            except Exception:
                # If parsing fails, treat as expired
                expiry = 0
        # Now compare with current time
        if time.time() < expiry:
            return st.session_state.token

    # Generate new token
    try:
        client_id = st.secrets["CLIENT_ID"]
        access_token = st.secrets["DHAN_ACCESS_TOKEN"]  # adjust secret name as needed

        # Initialize Dhan client
        dhan = dhanhq(client_id, access_token)

        # Request a new token – adjust based on your actual Dhan API
        # For Dhan, you typically exchange the access token for a session token
        # Replace with your actual token generation logic
        response = dhan.generate_token()  # Example – may need to use dhan.get_access_token()

        # Extract token and expiry
        token = response.get("access_token")
        expiry_str = response.get("expiry")  # Expected format: "2026-03-25T17:10:37Z"

        if not token or not expiry_str:
            raise ValueError("Invalid response from token API")

        # Convert expiry to Unix timestamp
        # Handle ISO format with 'Z'
        if expiry_str.endswith('Z'):
            expiry_str = expiry_str.replace('Z', '+00:00')
        expiry_ts = datetime.fromisoformat(expiry_str).timestamp()

        # Store in session state
        st.session_state.token = token
        st.session_state.expiry = expiry_ts

        return token

    except Exception as e:
        st.error(f"Token generation failed: {e}")
        return None
