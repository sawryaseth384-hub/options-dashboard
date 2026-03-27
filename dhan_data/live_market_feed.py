import json
import struct
import threading
import time

import websocket

from dhan_auth import get_token, CLIENT_ID

WS_URL = "wss://api-feed.dhan.co"
latest_price = 0


def _build_url(token, client_id):
    return f"{WS_URL}?version=2&token={token}&clientId={client_id}&authType=2"


def start_feed():
    def on_message(ws, message):
        global latest_price
        try:
            latest_price = struct.unpack("<f", message[8:12])[0]
        except Exception:
            return

    def on_error(ws, error):
        print("Live WS Error:", error)

    def on_close(ws, code, msg):
        print("Live WS Closed", code, msg)

    def on_open(ws):
        sub_msg = {
            "RequestCode": 15,
            "InstrumentCount": 1,
            "InstrumentList": [{"ExchangeSegment": "NSE_EQ", "SecurityId": "2885"}],
        }
        ws.send(json.dumps(sub_msg))

    def _loop():
        while True:
            try:
                url = _build_url(get_token(), CLIENT_ID)
                ws = websocket.WebSocketApp(
                    url,
                    on_message=on_message,
                    on_open=on_open,
                    on_error=on_error,
                    on_close=on_close,
                )
                ws.run_forever()
            finally:
                print("🔄 Reconnecting WebSocket...")
                time.sleep(2)

    threading.Thread(target=_loop, daemon=True).start()


def get_live_price():
    return latest_price
