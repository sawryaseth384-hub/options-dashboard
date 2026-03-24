import websocket
import struct
import threading
from core.token_manager import get_token
import streamlit as st

CLIENT_ID = st.secrets.get("CLIENT_ID", "")

ws_app = None
is_connected = False

DEPTH_DATA = {"bids": [], "asks": []}

# =========================
# SEGMENT MAP
# =========================
def map_ws_segment(segment):
    if segment == "NSE_FNO":
        return 2
    return 1  # IDX_I / NSE_EQ


# =========================
# PARSE DEPTH
# =========================
def parse_depth(message):
    global DEPTH_DATA

    try:
        body = message[12:]

        bids, asks = [], []

        for i in range(20):
            chunk = body[i*16:(i+1)*16]
            if len(chunk) < 16:
                continue

            price, qty, orders, side = struct.unpack('<fiii', chunk)

            level = {
                "price": round(price, 2),
                "qty": qty,
                "orders": orders
            }

            if side == 1:
                bids.append(level)
            else:
                asks.append(level)

        DEPTH_DATA = {"bids": bids, "asks": asks}

    except Exception as e:
        print("Parse error:", e)


# =========================
# CALLBACKS
# =========================
def on_open(ws):
    global is_connected
    is_connected = True
    print("✅ WS Connected")


def on_message(ws, message):
    if isinstance(message, bytes):
        parse_depth(message)


def on_error(ws, error):
    print("WS Error:", error)


def on_close(ws, close_status_code, close_msg):
    global is_connected
    is_connected = False
    print("❌ WS Closed")


# =========================
# START WS
# =========================
def start_depth_feed():
    global ws_app

    token = get_token()

    url = f"wss://api-feed.dhan.co?version=2&token={token}&clientId={CLIENT_ID}&authType=2"

    ws_app = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    threading.Thread(target=ws_app.run_forever, daemon=True).start()


# =========================
# SUBSCRIBE (BINARY)
# =========================
def subscribe_depth(security_id, segment):
    global ws_app

    if not ws_app or not is_connected:
        print("WS not ready")
        return

    exch = map_ws_segment(segment)

    # Header (12 bytes)
    header = struct.pack('<iii', 23, 20, int(CLIENT_ID))

    # Instrument (8 bytes)
    body = struct.pack('<ii', exch, int(security_id))

    packet = header + body

    try:
        ws_app.send(packet, opcode=websocket.ABNF.OPCODE_BINARY)
        print("Subscribed Depth")
    except Exception as e:
        print("Subscribe error:", e)


# =========================
# GET DATA
# =========================
def get_depth():
    return DEPTH_DATA
