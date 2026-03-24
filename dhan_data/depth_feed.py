import websocket
import json
import threading
import time
import streamlit as st
from core.token_manager import get_token

CLIENT_ID = st.secrets.get("CLIENT_ID")

ws = None
is_connected = False


# =========================
# MAP SEGMENT
# =========================
def map_segment(segment):
    return 2 if segment == "NSE_FNO" else 1


# =========================
# CALLBACKS
# =========================
def on_open(wsapp):
    global is_connected
    is_connected = True
    print("✅ WS CONNECTED")


def on_message(wsapp, message):
    print("📩 DATA RECEIVED")


def on_error(wsapp, error):
    print("❌ WS ERROR:", error)


def on_close(wsapp, close_status_code, close_msg):
    global is_connected
    is_connected = False
    print("❌ WS CLOSED")


# =========================
# START WS
# =========================
def start_depth_feed():
    global ws, is_connected

    token = get_token()

    if not token:
        print("❌ Token missing")
        return

    url = f"wss://api-feed.dhan.co?version=2&token={token}&clientId={CLIENT_ID}&authType=2"

    ws = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    def run():
        ws.run_forever(ping_interval=20, ping_timeout=10)

    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()

    # 🔥 WAIT FOR CONNECTION (IMPORTANT)
    for _ in range(10):
        if is_connected:
            return
        time.sleep(0.5)

    print("❌ WS FAILED TO CONNECT")


# =========================
# SAFE SUBSCRIBE
# =========================
def subscribe_depth(security_id, segment):

    global ws

    if not is_connected or ws is None:
        print("❌ WS NOT READY - SKIPPING SUBSCRIBE")
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
        print("✅ SUBSCRIBED SUCCESS")
    except websocket.WebSocketConnectionClosedException:
        print("❌ WS CLOSED - CANNOT SEND")
    except Exception as e:
        print("❌ SEND ERROR:", e)
