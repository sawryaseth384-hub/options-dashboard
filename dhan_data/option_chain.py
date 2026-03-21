import time
import requests

BASE_URL = "https://api.dhan.co/v2"

# 🔐 Replace with your credentials
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"
CLIENT_ID = "YOUR_CLIENT_ID"

# Rate limit control
_last_call_time = 0


# =========================
# 🔐 HEADERS
# =========================
def get_headers():
    return {
        "access-token": ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }


# =========================
# ⚡ SAFE REQUEST
# =========================
def safe_post(url, payload, retries=2):
    global _last_call_time

    for attempt in range(retries):
        # 🔥 Rate limit: 1 request per 3 sec
        now = time.time()
        wait = max(0, 3 - (now - _last_call_time))
        if wait > 0:
            time.sleep(wait)

        try:
            res = requests.post(
                url,
                headers=get_headers(),
                json=payload,
                timeout=10
            )

            _last_call_time = time.time()
            data = res.json()

            # ❌ Token / Auth error
            if data.get("status") == "failure":
                print("❌ API Failure:", data)
                return None

            return data

        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout (attempt {attempt+1}/{retries})")
            continue

        except Exception as e:
            print("❌ API Error:", e)
            return None

    print("❌ Max retries exceeded")
    return None


# =========================
# 📅 EXPIRY LIST
# =========================
def get_expiry_list(security_id=13):
    url = f"{BASE_URL}/optionchain/expirylist"

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": "IDX_I"
    }

    data = safe_post(url, payload)

    if not data or data.get("status") != "success":
        print("❌ Expiry fetch failed")
        return []

    return data.get("data", [])


# =========================
# 📊 OPTION CHAIN
# =========================
def get_option_chain(security_id=13):
    expiry_list = get_expiry_list(security_id)

    if not expiry_list:
        print("❌ No expiry found")
        return None

    # 🔥 Always nearest expiry (sorted)
    expiry = sorted(expiry_list)[0]

    url = f"{BASE_URL}/optionchain"

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": "IDX_I",
        "Expiry": expiry
    }

    print(f"📅 Using Expiry: {expiry}")

    data = safe_post(url, payload)

    # 🔍 Debug output
    print("📊 RAW OPTION CHAIN RESPONSE:")
    print(data)

    return data   # ✅ IMPORTANT (no wrapping)


# =========================
# 🚀 TEST RUN
# =========================
if __name__ == "__main__":
    print("🚀 Fetching Option Chain...")

    data = get_option_chain(13)  # NIFTY

    if data:
        print("✅ SUCCESS")
    else:
        print("❌ FAILED")
