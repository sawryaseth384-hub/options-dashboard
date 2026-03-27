import json
import threading
import time

import websocket

from dhan_auth import get_token, CLIENT_ID

depth_data = {"bids": [], "asks": []}


def _build_url(token, client_id):
    return f"wss://api-feed.dhan.co?version=2&token={token}&clientId={client_id}&authType=2"


def on_message(ws, message):
    global depth_data
    try:
        data = json.loads(message)
    except Exception:
        return
    if "depth" in data:
        depth = data["depth"]
        if isinstance(depth, dict):
            bids = depth.get("bids", [])
            asks = depth.get("asks", [])
            if isinstance(bids, list):
                depth["bids"] = bids[:5]
            if isinstance(asks, list):
                depth["asks"] = asks[:5]
        depth_data = depth


def on_error(ws, error):
    print("Depth Error:", error)


def on_close(ws, code, msg):
    print("Depth Closed", code, msg)


def on_open(ws):
    payload = {
        "RequestCode": 21,
        "InstrumentCount": 1,
        "InstrumentList": [{"ExchangeSegment": "NSE_EQ", "SecurityId": 2885}],
    }
    ws.send(json.dumps(payload))


def start_depth_feed():
    def _loop():
        while True:
            try:
                url = _build_url(get_token(), CLIENT_ID)
                ws = websocket.WebSocketApp(
                    url,
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                )
                ws.run_forever()
            finally:
                print("🔄 Reconnecting WebSocket...")
                time.sleep(2)

    threading.Thread(target=_loop, daemon=True).start()


def get_depth():
    return depth_data
