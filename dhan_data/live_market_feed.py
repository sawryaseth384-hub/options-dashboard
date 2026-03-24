import websocket
import json
import threading
import struct
import streamlit as st
from core.token_manager import get_token

CLIENT_ID = st.secrets.get("CLIENT_ID", "")
WS_URL = None
latest_data = {"ltp": 0, "ltt": 0, "volume": 0}
ws_app = None
is_connected = False
subscribed = set()

def map_ws_segment(segment):
    if segment == "NSE_FNO":
        return 2
    else:
        return 1

def parse_ticker(msg):
    try:
        ltp = struct.unpack('<f', msg[8:12])[0]
        ltt = struct.unpack('<i', msg[12:16])[0]
        latest_data["ltp"] = round(ltp, 2)
        latest_data["ltt"] = ltt
    except Exception as e:
        print("Ticker Parse Error:", e)

def parse_quote(msg):
    try:
        ltp = struct.unpack('<f', msg[8:12])[0]
        volume = struct.unpack('<i', msg[22:26])[0]
        latest_data["ltp"] = round(ltp, 2)
        latest_data["volume"] = volume
    except Exception as e:
        print("Quote Parse Error:", e)

def on_message(ws, message):
    try:
        if isinstance(message, bytes):
            code = message[0]
            if code == 2:
                parse_ticker(message)
            elif code == 4:
                parse_quote(message)
    except Exception as e:
        print("Message Error:", e)

def on_error(ws, error):
    print("WS ERROR:", error)

def on_close(ws, close_status_code, close_msg):
    global is_connected
    is_connected = False
    print("WS CLOSED")

def on_open(ws):
    global is_connected
    is_connected = True
    print("✅ LIVE CONNECTED")

def start_live_feed():
    global ws_app, WS_URL
    if ws_app is not None:
        return
    try:
        token = get_token()
        if not token:
            st.warning("Live feed not started: token missing.")
            return
        WS_URL = f"wss://api-feed.dhan.co?version=2&token={token}&clientId={CLIENT_ID}&authType=2"
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
        st.error(f"Live feed start error: {e}")

def subscribe_instrument(security_id, segment):
    global ws_app, is_connected, subscribed
    if ws_app is None or not is_connected:
        print("WS not ready")
        return
    key = f"{security_id}_{segment}"
    if key in subscribed:
        return
    subscribed.add(key)
    payload = {
        "RequestCode": 15,
        "InstrumentCount": 1,
        "InstrumentList": [
            {"ExchangeSegment": map_ws_segment(segment), "SecurityId": str(security_id)}
        ]
    }
    try:
        ws_app.send(json.dumps(payload))
    except Exception as e:
        print("Subscribe Error:", e)

def get_live_ltp():
    return latest_data.get("ltp", 0)
