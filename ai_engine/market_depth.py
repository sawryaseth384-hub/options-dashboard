import requests
from utils.config import DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID

def get_market_depth():

    url = "https://api.dhan.co/v2/marketfeed/ltp"

    headers = {
        "access-token": eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzczODA5MTAwLCJpYXQiOjE3NzM3MjI3MDAsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2Mjk5MjMwIn0.UVhOeBb2aD_qKfYfmm69icPXAlY7TT5FAhu1lNu3imOdXJyvfj5MR6FC8kwgXbvLS2I2Ix77tU0UX7ho0YpTkQ,
        "client-id": 1106299230,
        "Content-Type": "application/json"
    }

    payload = {
        "IDX_I": [13]   # ✅ FIX (Nifty)
    }

    try:
        return requests.post(url, headers=headers, json=payload).json()
    except Exception as e:
        return {"error": str(e)}
