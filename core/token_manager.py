import requests
import time
import pyotp

# 🔐 CONFIG (secrets में रख)
DHAN_CLIENT_ID = "1106299230"
PIN = "009988"
TOTP_SECRET = "DJUQ7WLHTV2ZVFHOTOORRT3VGHQJCMLV"

TOKEN_URL = "https://auth.dhan.co/app/generateAccessToken"

token_cache = {
    "token": None,
    "expiry": 0
}


# 🔥 dynamic TOTP
def get_totp():
    return pyotp.TOTP(TOTP_SECRET).now()


def generate_token():
    try:
        res = requests.post(
            TOKEN_URL,
            params={
                "dhanClientId": DHAN_CLIENT_ID,
                "pin": PIN,
                "totp": get_totp()   # 🔥 FIX
            },
            timeout=10
        )

        data = res.json()

        if "accessToken" in data:
            token_cache["token"] = data["accessToken"]

            # 🔥 FIX: API expiry use कर
            expiry_time = data.get("expiryTime")

            if expiry_time:
                from datetime import datetime
                expiry_dt = datetime.fromisoformat(expiry_time)
                token_cache["expiry"] = expiry_dt.timestamp() - 60  # buffer
            else:
                token_cache["expiry"] = time.time() + (23 * 60 * 60)

            print("✅ New Token Generated")

            return token_cache["token"]

        else:
            print("❌ Token Error:", data)
            return None

    except Exception as e:
        print("❌ Token Exception:", e)
        return None


def get_token():
    if token_cache["token"] is None or time.time() > token_cache["expiry"]:
        return generate_token()

    return token_cache["token"]
