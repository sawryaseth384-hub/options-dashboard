import websocket
import json
import struct
import threading
import streamlit as st

# =========================
# 🔥 GLOBAL STORE
# =========================
DEPTH_DATA = {
    "bids": [],
    "asks": []
}

ws_app = None
is_connected = False
subscribed = set()

# =========================
# 🔐 WS URL
# =========================
def get_ws_url():
    token = st.secrets["ACCESS_TOKEN"]
    client_id = st.secrets["CLIENT_ID"]
    return f"wss://depth-api-feed.dhan.co/twentydepth?token={token}&clientId={client_id}&authType=2"

# =========================
# 🔄 SEGMENT MAP (IMPORTANT)
# =========================
def map_ws_segment(segment):
    if segment == "IDX_I":
        return 1   # NSE_EQ (Index)
    elif segment == "NSE_FNO":
        return 2   # NSE_FNO
    return 1

# =========================
# 📊 PARSE DEPTH (20 LEVEL)
# =========================
def parse_depth(message):
    global DEPTH_DATA

    try:
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

# =========================
# ✅ OPEN
# =========================
def on_open(ws):
    global is_connected
    is_connected = True
    print("✅ Depth WS Connected")

# =========================
# ❌ ERROR
# =========================
def on_error(ws, error):
    print("Depth WS Error:", error)

# =========================
# 🔌 CLOSE
# =========================
def on_close(ws, code, msg):
    global is_connected
    is_connected = False
    print("Depth WS Closed")

# =========================
# 🚀 START WEBSOCKET
# =========================
def start_depth_feed():
    global ws_app

    if ws_app is not None:
        return

    ws_app = websocket.WebSocketApp(
        get_ws_url(),
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    thread = threading.Thread(target=ws_app.run_forever)
    thread.daemon = True
    thread.start()

# =========================
# 📡 SUBSCRIBE (FIXED)
# =========================
def subscribe_depth(security_id, segment):
    global ws_app, is_connected, subscribed

    if ws_app is None or not is_connected:
        print("Depth WS not ready")
        return

    key = f"{security_id}_{segment}"
    if key in subscribed:
        return

    subscribed.add(key)

    payload = {
        "RequestCode": 23,
        "InstrumentCount": 1,
        "InstrumentList": [
            {
                "ExchangeSegment": map_ws_segment(segment),
                "SecurityId": str(security_id)
            }
        ]
    }

    try:
        ws_app.send(json.dumps(payload))
    except Exception as e:
        print("Depth Subscribe Error:", e)

# =========================
# 📊 GET DEPTH
# =========================
def get_depth():
    return DEPTH_DATA
