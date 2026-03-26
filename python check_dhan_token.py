import requests
import json

# 🔧 YAHAN APNA TOKEN AUR CLIENT ID DAALEIN
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzc0MjY4MTk5LCJpYXQiOjE3NzQxODE3OTksInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2Mjk5MjMwIn0.E26wPlTIRooX3uhJCxWoP3gwEYiMds5FdbmPc_G3J53lFm8Eo7L3kcaYfSwTw-vLTtBqOLmqGuaBNw7L32M2Sg"
BASE_URL = "https://api.dhan.co"

def check_profile():
    url = f"{BASE_URL}/v2/profile"
    headers = {"access-token": ACCESS_TOKEN}
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
    url = f"{BASE_URL}/v2/optionchain/expirylist"
    headers = {"access-token": ACCESS_TOKEN, "Content-Type": "application/json"}
    payload = {"UnderlyingScrip": 13, "UnderlyingSeg": "NSE_FNO"}
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code == 401:
        print("❌ Unauthorized - check token")
        return None
    if resp.status_code == 200:
        data = resp.json()
        if data.get("status") == "success":
            expiries = data.get("data", [])
            print(f"✅ Expiry list works. Found {len(expiries)} dates.")
            return expiries
    print("❌ Expiry list failed:", resp.text)
    return None

def test_option_chain(expiry):
    url = f"{BASE_URL}/v2/optionchain"
    headers = {"access-token": ACCESS_TOKEN, "Content-Type": "application/json"}
    payload = {"UnderlyingScrip": 13, "UnderlyingSeg": "NSE_FNO", "Expiry": expiry}
    print(f"\n📤 Sending payload to option chain:\n{json.dumps(payload, indent=2)}")
    resp = requests.post(url, headers=headers, json=payload)
    print(f"📥 Response status: {resp.status_code}")
    if resp.status_code == 401:
        print("❌ Unauthorized - check token")
        return
    try:
        data = resp.json()
        print("Response data:", json.dumps(data, indent=2)[:500])
        if "data" in data and "oc" in data["data"]:
            strikes = len(data["data"]["oc"])
            print(f"✅ Option chain works! Found {strikes} strikes.")
        else:
            print("❌ Option chain failed. Check error above.")
    except:
        print("❌ Could not parse JSON response:", resp.text)

if __name__ == "__main__":
    print("🔍 Testing Dhan API token...")
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
