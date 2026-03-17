import requests
from utils.config import DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID

def get_market_quote():

    url = "https://api.dhan.co/v2/marketfeed/ltp"

    headers = {
        "access-token": eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzczNjc3MTA0LCJpYXQiOjE3NzM1OTA3MDQsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2Mjk5MjMwIn0.jnn6DApddObFVi53XcsMcMgEJGn8TgGyWL6ZjLs3sAYZ4dQUd4Ope8PZQ5Jy7rPPdKK3sIm9Tn5i7ZuXplziow,
        "client-id": 1106299230,
        "Content-Type": "application/json"
    }

    payload = {
        "NSE_INDEX": ["Nifty 50", "Nifty Bank"]
    }

    response = requests.post(url, headers=headers, json=payload)

    return response.json()
