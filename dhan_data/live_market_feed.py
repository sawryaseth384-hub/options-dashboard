import websocket
import json
import threading
import struct

from dhan_auth import get_token, CLIENT_ID

WS_URL = "wss://api-feed.dhan.co"

latest_price = 0

def start_feed(token=None, client_id=None):
    token = token or get_token()
    client_id = client_id or CLIENT_ID
    if not token or not client_id:
        print("❌ Missing token or client id for live feed.")
        return

    def on_message(ws, message):
        global latest_price

        try:
            # 🔥 decode binary (LTP packet)
            ltp = struct.unpack('<f', message[8:12])[0]
            latest_price = ltp

        except:
            pass

    def on_open(ws):
        print("✅ WebSocket Connected")

        sub_msg = {
            "RequestCode": 15,
            "InstrumentCount": 1,
            "InstrumentList": [
                {
                    "ExchangeSegment": "NSE_EQ",
                    "SecurityId": "2885"
                }
            ]
        }

        ws.send(json.dumps(sub_msg))

    url = f"{WS_URL}?version=2&token={token}&clientId={client_id}&authType=2"

    ws = websocket.WebSocketApp(
        url,
        on_message=on_message,
        on_open=on_open
    )

    thread = threading.Thread(target=ws.run_forever)
    thread.daemon = True
    thread.start()

def get_live_price():
    return latest_price
