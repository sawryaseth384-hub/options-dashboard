import websocket
import json
import struct
import threading
import streamlit as st
from core.token_manager import get_token

CLIENT_ID = st.secrets.get("CLIENT_ID", "")
WS_URL = None  # will be set after token is known

DEPTH_DATA = {"bids": [], "asks": []}
ws_app = None
is_connected = False
subscribed = set()

def map_ws_segment(segment):
    if segment == "NSE_FNO":
        return 2
    else:
        return 1

def parse_depth(message):
    global DEPTH_DATA
    try:
        code = message[2]
        body = message[12:]
        levels = []
        for i in range(20):
            start = i * 16
            chunk = body[start:start+16]
            if len(chunk) < 16:
                continue
            price = struct.unpack('<d', chunk[0:8])[0]
            qty = struct.unpack('<I', chunk[8:12])[0]
            orders = struct.unpack('<I', chunk[12:16])[0]
            levels.append({"price": round(price, 2), "qty": qty, "orders": orders})
        if code == 41:
            DEPTH_DATA["bids"] = levels
        elif code == 51:
            DEPTH_DATA["asks"] = levels
    except Exception as e:
        print("Depth Parse Error:", e)

def on_message(ws, message):
    if isinstance(message, bytes):
        parse_depth(message)

def on_open(ws):
    global is_connected
    is_connected = True
    print("✅ Depth WS Connected")

def on_error(ws, error):
    print("Depth WS Error:", error)

def on_close(ws, code, msg):
    global is_connected
    is_connected = False
    print("Depth WS Closed")

def start_depth_feed():
    global ws_app, WS_URL
    if ws_app is not None:
        return
    try:
        token = get_token()
        if not token:
            st.warning("Depth feed not started: token missing.")
            return
        WS_URL = f"wss://depth-api-feed.dhan.co/twentydepth?token={token}&clientId={CLIENT_ID}&authType=2"
        ws_app = websocket.WebSocketApp(
            WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        thread = threading.Thread(target=ws_app.run_forever)
        thread.daemon = True
        thread.start()
    except Exception as e:
        st.error(f"Depth feed start error: {e}")

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
            {"ExchangeSegment": map_ws_segment(segment), "SecurityId": str(security_id)}
        ]
    }
    try:
        ws_app.send(json.dumps(payload))
    except Exception as e:
        print("Depth Subscribe Error:", e)

def get_depth():
    return DEPTH_DATA
