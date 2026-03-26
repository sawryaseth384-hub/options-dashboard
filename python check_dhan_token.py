import json

from core.token_manager import get_access_token, get_client_id
from dhan_data.client import sdk_get_quote
from dhan_data.option_chain import get_expiry_list, get_option_chain


def check_quote():
    data, err = sdk_get_quote(13, "NSE_INDEX")
    if err:
        print("❌ Quote API failed:", err)
        return None
    print("✅ Quote fetched. Token is valid.")
    return data

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
    client_id = get_client_id()
    if not token or not client_id:
        print("❌ Missing credentials. Check CLIENT_ID and DHAN_ACCESS_TOKEN.")
        exit()
    if not check_quote():
        exit()
    expiries = test_expiry_list()
    if not expiries:
        exit()
    test_option_chain(expiries[0])
