import requests

def run_diagnostics(token, client_id):
    report = {}

    # =========================
    # 1. TOKEN CHECK
    # =========================
    if not token or len(token) < 20:
        report["token"] = "❌ Invalid / Missing Token"
    else:
        report["token"] = "✅ Token format OK"

    # =========================
    # 2. CLIENT ID CHECK
    # =========================
    if not client_id:
        report["client"] = "❌ Missing Client ID"
    else:
        report["client"] = f"✅ Client ID: {client_id}"

    # =========================
    # 3. MARKET API TEST
    # =========================
    try:
        url = "https://api.dhan.co/v2/marketfeed/ltp"
        headers = {
            "access-token": token,
            "client-id": client_id,
            "Content-Type": "application/json"
        }
        payload = {"NSE_EQ": [11536]}

        res = requests.post(url, headers=headers, json=payload).json()

        if res.get("status") == "success":
            report["market_api"] = "✅ Market API Working"
        else:
            report["market_api"] = f"❌ Market API Error: {res}"

    except Exception as e:
        report["market_api"] = f"❌ Crash: {str(e)}"

    # =========================
    # 4. OPTION CHAIN TEST
    # =========================
    try:
        url = "https://api.dhan.co/v2/optionchain/expirylist"
        payload = {
            "UnderlyingScrip": 13,
            "UnderlyingSeg": "IDX_I"
        }

        res = requests.post(url, headers=headers, json=payload).json()

        if res.get("data"):
            report["option_chain"] = "✅ Expiry Data OK"
        else:
            report["option_chain"] = f"❌ No Expiry: {res}"

    except Exception as e:
        report["option_chain"] = f"❌ Crash: {str(e)}"

    return report
