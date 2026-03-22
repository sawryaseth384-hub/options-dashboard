import requests
import os
import json

def refresh_token(current_token, client_id):
    url = "https://api.dhan.co/v2/RenewToken"
    headers = {
        "access-token": current_token,
        "dhanClientId": client_id
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        new_token = response.json().get("accessToken")
        return new_token
    else:
        print(f"Failed to renew token: {response.text}")
        return None

if __name__ == "__main__":
    # Read current token from environment (or secret)
    current = os.environ.get("ACCESS_TOKEN")
    client = os.environ.get("CLIENT_ID")
    if not current or not client:
        print("Missing ACCESS_TOKEN or CLIENT_ID")
        exit(1)

    new_token = refresh_token(current, client)
    if new_token:
        print(f"New token: {new_token}")
        # Here you would update the secret in Streamlit Cloud
        # (see next step)
