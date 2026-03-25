import websocket
import threading
import struct
import time
import streamlit as st
from core.token_manager import get_token

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
        "NSE_FNO": 2
    }.get(seg, 1)


# =========================
# PARSE BINARY DEPTH
# =========================
def parse_depth(message):
    global DEPTH_DATA

    try:
        body = message[12:]  # skip header

        bids = []
        asks = []

        for i in range(20):
            chunk = body[i*16:(i+1)*16]

            if len(chunk) < 16:
                continue

            price = struct.unpack('<f', chunk[0:4])[0]
            qty = struct.unpack('<i', chunk[4:8])[0]
            orders = struct.unpack('<i', chunk[8:12])[0]
            side = struct.unpack('<i', chunk[12:16])[0]

            data = {
                "price": round(price, 2),
                "qty": qty,
                "orders": orders
            }

            if side == 1:
                bids.append(data)
            else:
                asks.append(data)

        DEPTH_DATA = {
            "bids": bids,
            "asks": asks
        }

    except Exception as e:
        print("Parse Error:", e)


# =========================
# ON MESSAGE
# =========================
def on_message(ws, message):
    if isinstance(message, bytes):
        parse_depth(message)


# =========================
# ON OPEN
# =========================
def on_open(ws):
    global is_connected
    is_connected = True
    print("✅ Depth WS Connected")


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
        on_message=on_message
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

    ws.send(json.dumps(payload))
    print(f"✅ Subscribed Depth: {security_id}")


# =========================
# GET DATA
# =========================
def get_depth():
    return DEPTH_DATA
