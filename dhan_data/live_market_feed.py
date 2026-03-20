import websocket
import json
import threading
import struct
import streamlit as st

# =========================
# 🔐 CONFIG
# =========================
TOKEN = st.secrets["ACCESS_TOKEN"]
CLIENT_ID = st.secrets["CLIENT_ID"]

WS_URL = f"wss://api-feed.dhan.co?version=2&token={TOKEN}&clientId={CLIENT_ID}&authType=2"

# =========================
# 🔥 GLOBAL STATE
# =========================
latest_data = {
    "ltp": 0,
    "time": 0,
    "symbol": None
}

ws_app = None


# =========================
# 🔥 PARSE TICKER (CODE 2)
# =========================
def parse_ticker(message):
    try:
        # header (8 bytes skip)
        ltp = struct.unpack('<f', message[8:12])[0]
        ltt = struct.unpack('<i', message[12:16])[0]

        latest_data["ltp"] = round(ltp, 2)
        latest_data["time"] = ltt

    except Exception as e:
        print("Parse Error:", e)


# =========================
# 🔥 ON MESSAGE
# =========================
def on_message(ws, message):
    if isinstance(message, bytes):

        # first byte = response code
        response_code = message[0]

        if response_code == 2:  # ticker packet
            parse_ticker(message)


def on_error(ws, error):
    print("WS ERROR:", error)


def on_close(ws, close_status_code, close_msg):
    print("WS CLOSED")


def on_open(ws):
    print("✅ WS CONNECTED")


# =========================
# 🚀 START CONNECTION
# =========================
def start_live_feed():
    global ws_app

    if ws_app:
        return  # already running

    def run():
        global ws_app

        ws_app = websocket.WebSocketApp(
            WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )

        ws_app.run_forever()

    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()


# =========================
# 🔄 SUBSCRIBE (DYNAMIC)
# =========================
def subscribe_instrument(security_id, segment):
    global ws_app

    if not ws_app:
        return

    payload = {
        "RequestCode": 15,  # ticker
        "InstrumentCount": 1,
        "InstrumentList": [
            {
                "ExchangeSegment": segment,
                "SecurityId": str(security_id)
            }
        ]
    }

    ws_app.send(json.dumps(payload))
    latest_data["symbol"] = security_id


# =========================
# 📊 GET LTP
# =========================
def get_live_ltp():
    return latest_data["ltp"]
