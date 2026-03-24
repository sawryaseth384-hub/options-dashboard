import websocket
import threading
import json
import time
import streamlit as st
from core.token_manager import get_token

# =========================
# GLOBALS
# =========================
ws = None
is_connected = False

DEPTH_DATA = {
    "bids": [],
    "asks": []
}


# =========================
# SEGMENT MAP
# =========================
def map_segment(seg):
    return {
        "NSE_EQ": 1,
        "NSE_FNO": 2,
        "IDX_I": 0   # ❌ INDEX NOT SUPPORTED (IMPORTANT)
    }.get(seg, 1)


# =========================
# ON MESSAGE
# =========================
def on_message(ws, message):
    global DEPTH_DATA

    try:
        data = json.loads(message)

        if "Depth" in data:
            DEPTH_DATA = data["Depth"]

    except:
        pass


# =========================
# ON OPEN
# =========================
def on_open(ws):
    global is_connected
    is_connected = True
    print("✅ Depth WS Connected")


# =========================
# ON CLOSE
# =========================
def on_close(ws, a, b):
    global is_connected
    is_connected = False
    print("❌ Depth WS Closed")


# =========================
# START WS
# =========================
def start_depth_feed():
    global ws

    token = get_token()
    client_id = st.secrets["CLIENT_ID"]

    url = f"wss://api-feed.dhan.co?version=2&token={token}&clientId={client_id}&authType=2"

    ws = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message,
        on_close=on_close
    )

    thread = threading.Thread(target=ws.run_forever)
    thread.daemon = True
    thread.start()

    time.sleep(2)


# =========================
# SUBSCRIBE
# =========================
def subscribe_depth(security_id, segment):

    if segment == "IDX_I":
        print("❌ Index depth not supported")
        return

    if not ws or not is_connected:
        print("❌ WS not connected")
        return

    payload = {
        "RequestCode": 23,
        "InstrumentCount": 1,
        "InstrumentList": [
            {
                "ExchangeSegment": map_segment(segment),
                "SecurityId": str(security_id)
            }
        ]
    }

    try:
        ws.send(json.dumps(payload))
        print(f"✅ Subscribed Depth: {security_id}")

    except Exception as e:
        print("❌ Subscribe Error:", e)


# =========================
# GET DATA
# =========================
def get_depth():
    return DEPTH_DATA
