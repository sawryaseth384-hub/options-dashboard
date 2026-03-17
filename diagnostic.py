import requests
import os

# =========================
# 🔥 LOAD CONFIG
# =========================
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")

print("========== 🔍 SYSTEM DIAGNOSTIC ==========\n")

# =========================
# 1. TOKEN CHECK
# =========================
print("1️⃣ Checking ENV Variables...")

if not ACCESS_TOKEN:
    print("❌ ACCESS_TOKEN missing")
else:
    print("✅ ACCESS_TOKEN found")

if not CLIENT_ID:
    print("❌ CLIENT_ID missing")
else:
    print("✅ CLIENT_ID found")

if not ACCESS_TOKEN or not CLIENT_ID:
    print("\n🚨 FIX: Set ENV variables in Render\n")
    exit()

# =========================
# 2. MARKET API TEST
# =========================
print("\n2️⃣ Testing Market API...")

url = "https://api.dhan.co/v2/marketfeed/ltp"

headers = {
    "access-token": ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json"
}

payload = {
    "NSE_EQ": [11536]
}

try:
    res = requests.post(url, headers=headers, json=payload)
    data = res.json()

    if data.get("status") == "success":
        print("✅ Market API Working")
    else:
        print("❌ Market API Error:", data)

except Exception as e:
    print("❌ Market API Crash:", e)

# =========================
# 3. OPTION CHAIN TEST
# =========================
print("\n3️⃣ Testing Option Chain...")

url = "https://api.dhan.co/v2/optionchain/expirylist"

payload = {
    "UnderlyingScrip": 13,
    "UnderlyingSeg": "IDX_I"
}

try:
    res = requests.post(url, headers=headers, json=payload)
    data = res.json()

    if data.get("data"):
        print("✅ Expiry List Working")
        print("👉 Sample Expiry:", data["data"][0])
    else:
        print("❌ No Expiry Found:", data)

except Exception as e:
    print("❌ Option Chain Crash:", e)

# =========================
# 4. FINAL RESULT
# =========================
print("\n========== 🧠 RESULT ==========")

print("""
👉 If all ✅ → system OK
👉 If Market ❌ → token issue
👉 If Expiry ❌ → option chain issue
👉 If ENV ❌ → config problem
""")
