import requests

# 🔥 PUT YOUR VALUES
CLIENT_ID = "1106299230"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzczODg1OTg5LCJpYXQiOjE3NzM3OTk1ODksInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2Mjk5MjMwIn0.vRYxbB0OWqCIQ02J741rAoGugbSg3DV2bU1Ub-un-mAs-8QMzTFKCbnIp0RiC3AGASX4zVfmFS1nHRRYaYPmkQ"

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
