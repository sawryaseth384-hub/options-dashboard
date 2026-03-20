import websocket
import json
import struct
import threading
import streamlit as st

DEPTH_DATA = {
    "bids": [],
    "asks": []
}


def get_ws_url():
    token = st.secrets["ACCESS_TOKEN"]
    client_id = st.secrets["CLIENT_ID"]

    return f"wss://depth-api-feed.dhan.co/twentydepth?token={token}&clientId={client_id}&authType=2"


# =========================
# 📊 PARSE DEPTH (20 LEVEL)
# =========================
def parse_depth(message):
    global DEPTH_DATA

    try:
        header = message[:12]

        # response code
        code = message[2]

        body = message[12:]

        levels = []

        for i in range(20):
            start = i * 16
            chunk = body[start:start + 16]

            if len(chunk) < 16:
                continue

            price = struct.unpack('<d', chunk[0:8])[0]
            qty = struct.unpack('<I', chunk[8:12])[0]
            orders = struct.unpack('<I', chunk[12:16])[0]

            levels.append({
                "price": round(price, 2),
                "qty": qty,
                "orders": orders
            })

        # 41 = BID, 51 = ASK
        if code == 41:
            DEPTH_DATA["bids"] = levels

        elif code == 51:
            DEPTH_DATA["asks"] = levels

    except Exception as e:
        print("Depth Parse Error:", e)


# =========================
# 📡 MESSAGE
# =========================
def on_message(ws, message):
    if isinstance(message, bytes):
        parse_depth(message)


def on_open(ws):
    print("✅ Depth WS Connected")

    payload = {
        "RequestCode": 23,
        "InstrumentCount": 1,
        "InstrumentList": [
            {
                "ExchangeSegment": "NSE_FNO",
                "SecurityId": "13"
            }
        ]
    }

    ws.send(json.dumps(payload))


def start_ws():
    ws = websocket.WebSocketApp(
        get_ws_url(),
        on_message=on_message,
        on_open=on_open
    )

    ws.run_forever()


# =========================
# 🚀 START THREAD
# =========================
def start_depth_feed():
    thread = threading.Thread(target=start_ws)
    thread.daemon = True
    thread.start()


def get_depth():
    return DEPTH_DATA
