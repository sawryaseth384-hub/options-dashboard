import websocket
import json
import threading
from core.token_manager import get_headers

ws = None
depth_data = {"bids": [], "asks": []}

def on_message(ws, message):
    global depth_data
    data = json.loads(message)

    if "depth" in data:
        depth_data = data["depth"]

def on_error(ws, error):
    print("Depth Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("Depth Closed")

def on_open(ws):
    print("Depth Connected")

    # 🔥 subscribe RELIANCE
    payload = {
        "RequestCode": 21,
        "InstrumentCount": 1,
        "InstrumentList": [
            {
                "ExchangeSegment": "NSE_EQ",
                "SecurityId": 2885
            }
        ]
    }

    ws.send(json.dumps(payload))

def start_depth_feed():
    global ws

    headers = get_headers()

    ws = websocket.WebSocketApp(
        "wss://api-feed.dhan.co",
        header=[
            f"access-token: {headers['access-token']}",
            f"client-id: {headers['client-id']}"
        ],
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    thread = threading.Thread(target=ws.run_forever)
    thread.daemon = True
    thread.start()

def get_depth():
    return depth_data
