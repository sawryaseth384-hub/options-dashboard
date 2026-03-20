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
# 🔥 GLOBAL STORE
# =========================
latest_data = {
    "ltp": 0,
    "ltt": 0,
    "volume": 0
}

ws_app = None


# =========================
# 🔥 PARSE TICKER (CODE 2)
# =========================
def parse_ticker(msg):
    ltp = struct.unpack('<f', msg[8:12])[0]
    ltt = struct.unpack('<i', msg[12:16])[0]

    latest_data["ltp"] = round(ltp, 2)
    latest_data["ltt"] = ltt


# =========================
# 🔥 PARSE QUOTE (CODE 4)
# =========================
def parse_quote(msg):
    ltp = struct.unpack('<f', msg[8:12])[0]
    volume = struct.unpack('<i', msg[22:26])[0]

    latest_data["ltp"] = round(ltp, 2)
    latest_data["volume"] = volume


# =========================
# 🔥 MESSAGE HANDLER
# =========================
def on_message(ws, message):
    try:
        if isinstance(message, bytes):

            code = message[0]

            if code == 2:
                parse_ticker(message)

            elif code == 4:
                parse_quote(message)

    except Exception as e:
        print("Parse Error:", e)


def on_error(ws, error):
    print("WS ERROR:", error)


def on_close(ws, close_status_code, close_msg):
    print("WS CLOSED")


def on_open(ws):
    print("✅ LIVE CONNECTED")


# =========================
# 🚀 START WS
# =========================
def start_live_feed():
    global ws_app

    if ws_app:
        return

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
# 📡 SUBSCRIBE
# =========================
def subscribe_instrument(security_id, segment):
    global ws_app

    if not ws_app:
        return

    payload = {
        "RequestCode": 15,
        "InstrumentCount": 1,
        "InstrumentList": [
            {
                "ExchangeSegment": segment,
                "SecurityId": str(security_id)
            }
        ]
    }

    ws_app.send(json.dumps(payload))


# =========================
# 📊 GET DATA
# =========================
def get_live_ltp():
    return latest_data["ltp"]
