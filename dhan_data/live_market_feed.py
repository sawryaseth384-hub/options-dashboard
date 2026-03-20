import websocket
import json
import struct
import threading
import streamlit as st

LIVE_DATA = {}


def get_ws_url():
    token = st.secrets["ACCESS_TOKEN"]
    client_id = st.secrets["CLIENT_ID"]

    return f"wss://api-feed.dhan.co?version=2&token={token}&clientId={client_id}&authType=2"


# =========================
# 📡 PARSE BINARY (LTP)
# =========================
def parse_ltp(binary_data):
    try:
        # little endian
        ltp = struct.unpack('<f', binary_data[8:12])[0]
        return ltp
    except:
        return None


# =========================
# 📡 ON MESSAGE
# =========================
def on_message(ws, message):
    global LIVE_DATA

    if isinstance(message, bytes):
        ltp = parse_ltp(message)

        if ltp:
            LIVE_DATA["ltp"] = ltp


def on_open(ws):
    print("✅ WebSocket Connected")

    payload = {
        "RequestCode": 15,
        "InstrumentCount": 1,
        "InstrumentList": [
            {
                "ExchangeSegment": "IDX_I",
                "SecurityId": "13"   # NIFTY
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
def start_live_feed():
    thread = threading.Thread(target=start_ws)
    thread.daemon = True
    thread.start()


def get_live_ltp():
    return LIVE_DATA.get("ltp", 0)
