import websocket
import json
import threading
import struct
import streamlit as st

# 👉 global store
live_data = {
    "ltp": 0
}


def decode_ltp(message):
    try:
        # byte 9–12 = LTP (float32 little endian)
        ltp = struct.unpack('<f', message[8:12])[0]
        return ltp
    except:
        return None


def start_ws():

    token = st.secrets.get("DHAN_ACCESS_TOKEN") or st.secrets.get("ACCESS_TOKEN")
    client_id = st.secrets.get("CLIENT_ID") or st.secrets.get("DHAN_CLIENT_ID") or ""
    url = f"wss://api-feed.dhan.co?version=2&token={token}&clientId={client_id}&authType=2"

    def on_open(ws):
        print("✅ Connected")

        payload = {
            "RequestCode": 15,
            "InstrumentCount": 1,
            "InstrumentList": [
                {
                    "ExchangeSegment": "NSE_EQ",
                    "SecurityId": "13"   # BANKNIFTY
                }
            ]
        }

        ws.send(json.dumps(payload))

    def on_message(ws, message):
        ltp = decode_ltp(message)
        if ltp:
            live_data["ltp"] = ltp
            print("LIVE LTP:", ltp)

    def on_error(ws, error):
        print("❌ Error:", error)

    def on_close(ws):
        print("🔴 Closed")

    ws = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    ws.run_forever()


def run_live():
    thread = threading.Thread(target=start_ws)
    thread.daemon = True
    thread.start()
