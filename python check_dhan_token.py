import json

import requests

from core.token_manager import get_access_token, get_headers
from dhan_data.option_chain import get_expiry_list, get_option_chain

BASE_URL = "https://api.dhan.co/v2"

def check_profile():
    url = f"{BASE_URL}/profile"
    headers = get_headers()
    resp = requests.get(url, headers=headers)
    if resp.status_code == 401:
        print("❌ Unauthorized - check token")
        return None
    if resp.status_code == 200:
        data = resp.json()
        print("✅ Token valid.")
        print(f"   Token expiry: {data.get('tokenValidity')}")
        print(f"   Data Plan status: {data.get('dataPlan')}")
        return data
    else:
        print("❌ Profile API failed:", resp.json())
        return None

def test_expiry_list():
    expiries, err = get_expiry_list(13, "NSE_INDEX")
    if err:
        print("❌ Expiry list failed:", err)
        return None
    print(f"✅ Expiry list works. Found {len(expiries)} dates.")
    return expiries

def test_option_chain(expiry):
    print(f"\n📤 Sending payload to option chain:\n{json.dumps({'UnderlyingScrip': 13, 'UnderlyingSeg': 'NSE_INDEX', 'expiryDate': expiry}, indent=2)}")
    data, err = get_option_chain(13, expiry=expiry, segment="NSE_INDEX")
    if err:
        print("❌ Option chain failed:", err)
        return
    print("Response data:", json.dumps(data, indent=2)[:500])
    if "data" in data and "oc" in data["data"]:
        strikes = len(data["data"]["oc"])
        print(f"✅ Option chain works! Found {strikes} strikes.")
    else:
        print("❌ Option chain failed. Check error above.")

if __name__ == "__main__":
    print("🔍 Testing Dhan API token...")
    token = get_access_token()
    if not token:
        print("❌ Missing Dhan token. Check CLIENT_ID, PIN, and TOTP_SECRET.")
        exit()
    profile = check_profile()
    if not profile:
        exit()
    if profile.get("dataPlan") != "Active":
        print("❌ Data Plan is NOT active.")
        exit()
    expiries = test_expiry_list()
    if not expiries:
        exit()
    test_option_chain(expiries[0])
