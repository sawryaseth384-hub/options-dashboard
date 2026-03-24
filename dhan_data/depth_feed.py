import websocket
import json
import threading
import streamlit as st
from core.token_manager import get_token

# =========================
# CONFIG
# =========================
CLIENT_ID = st.secrets.get("CLIENT_ID", "")

ws = None
is_connected = False

LIVE_DATA = {}

# =========================
# CONNECT
# =========================
def start_ws():
    global ws, is_connected

    token = get_token()

    url = f"wss://api.dhan.co/ws/v2/marketfeed?client-id={CLIENT_ID}&access-token={token}"

    def on_open(ws):
        global is_connected
        is_connected = True
        print("✅ WebSocket Connected")

        # 🔥 Subscribe after connect
        subscribe(ws)

    def on_message(ws, message):
        try:
            data = json.loads(message)
            print("DATA:", data)

            # Store latest data
            if "data" in data:
                for seg in data["data"]:
                    for sec_id, val in data["data"][seg].items():
                        LIVE_DATA[sec_id] = val

        except Exception as e:
            print("Parse error:", e)

    def on_error(ws, error):
        print("WS Error:", error)

    def on_close(ws, close_status_code, close_msg):
        global is_connected
        is_connected = False
        print("❌ WebSocket Closed")

    ws = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    threading.Thread(target=ws.run_forever, daemon=True).start()


# =========================
# SUBSCRIBE
# =========================
def subscribe(ws):
    payload = {
        "messageType": "subscribe",
        "instruments": {
            "IDX_I": [13],          # NIFTY
            "NSE_FNO": [49081]      # Example FNO
        }
    }

    ws.send(json.dumps(payload))


# =========================
# GET LTP
# =========================
def get_live_ltp(security_id):
    return LIVE_DATA.get(str(security_id), {}).get("last_price", 0)
