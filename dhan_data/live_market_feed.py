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
# 🔥 PARSE TICKER (Code 2)
# =========================
def parse_ticker(msg):
    try:
        ltp = struct.unpack('f', msg[8:12])[0]
        ltt = struct.unpack('i', msg[12:16])[0]

        latest_data["ltp"] = round(ltp, 2)
        latest_data["ltt"] = ltt

    except Exception as e:
        print("Ticker Parse Error:", e)


# =========================
# 🔥 PARSE QUOTE (Code 4)
# =========================
def parse_quote(msg):
    try:
        ltp = struct.unpack('f', msg[8:12])[0]
        volume = struct.unpack('i', msg[22:26])[0]

        latest_data["ltp"] = round(ltp, 2)
        latest_data["volume"] = volume

    except Exception as e:
        print("Quote Parse Error:", e)


# =========================
# 📡 ON MESSAGE
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
        print("Message Error:", e)


# =========================
# ❌ ERROR
# =========================
def on_error(ws, error):
    print("WS ERROR:", error)


# =========================
# 🔌 CLOSE
# =========================
def on_close(ws, close_status_code, close_msg):
    print("WS CLOSED")


# =========================
# ✅ OPEN
# =========================
def on_open(ws):
    print("✅ LIVE CONNECTED")


# =========================
# 🚀 START WEBSOCKET
# =========================
def start_live_feed():
    global ws_app

    if ws_app is not None:
        return

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


# =========================
# 📡 SUBSCRIBE
# =========================
def subscribe_instrument(security_id, segment):
    global ws_app

    if ws_app is None:
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

    try:
        ws_app.send(json.dumps(payload))
    except Exception as e:
        print("Subscribe Error:", e)


# =========================
# 💰 GET LIVE LTP
# =========================
def get_live_ltp():
    return latest_data.get("ltp", 0)
