import requests

def get_option_chain(security_id, segment, expiry):

    url = "https://api.dhan.co/v2/optionchain"

    headers = {
        "access-token": "YOUR_TOKEN",
        "client-id": "YOUR_CLIENT_ID",
        "Content-Type": "application/json"
    }

    payload = {
        "UnderlyingScrip": security_id,
        "UnderlyingSeg": segment,
        "Expiry": expiry
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()

    return {}
