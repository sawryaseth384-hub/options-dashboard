import requests

# 🔥 PUT YOUR VALUES
CLIENT_ID = "1106299230"
ACCESS_TOKEN = "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJwYXJ0bmVySWQiOiIiLCJkaGFuQ2xpZW50SWQiOiIyNTA2MTg2NzU5Iiwid2ViaG9va1VybCI6IiIsImlzcyI6ImRoYW4iLCJleHAiOjE3NzY3NzU5NzN9.PkT_v5z-hMx0pPaTJiaBeAlw-MpFraey1GM26Svurdzc6kgSLlIrgfAnLWt7ne2ViramoGPvfklbWu6TR4BHsw"

url = "https://api.dhan.co/v2/marketfeed/quote"

headers = {
    "access-token": ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

payload = {
    "NSE_FNO": [49081]
}

res = requests.post(url, headers=headers, json=payload)

print("STATUS:", res.status_code)
print("RESPONSE:", res.text)
