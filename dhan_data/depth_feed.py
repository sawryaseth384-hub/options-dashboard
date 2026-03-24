import websocket
import struct
import threading
import json
import time
import streamlit as st
from core.token_manager import get_token

CLIENT_ID = st.secrets.get("CLIENT_ID", "")

ws = None
is_connected = False

# Store data
DEPTH_DATA = {"bids": [], "asks": []}
LTP_DATA = 0

# =========================
# SEGMENT MAP
# =========================
def map_ws_segment(segment):
    if segment == "NSE_FNO":
        return 2
    elif segment == "IDX_I":
        return 1
    else:
        return 1


# =========================
# PARSE LTP (BINARY)
# =========================
def parse_ltp(message):
    global LTP_DATA
    try:
        # skip header
        body = message[12:]

        # LTP at first 4 bytes
        ltp = struct.unpack('f', body[:4])[0]
        LTP_DATA = round(ltp, 2)

    except Exception as e:
        print("LTP parse error:", e)


# =========================
# PARSE DEPTH (BINARY)
# =========================
def parse_depth(message):
    global DEPTH_DATA

    try:
        body = message[12:]

        bids = []
        asks = []

        for i in range(20):
            chunk = body[i*16:(i+1)*16]
            if len(chunk) < 16:
                continue

            price, qty, orders, side = struct.unpack('fiii', chunk)

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
        print("Depth parse error:", e)


# =========================
# WS EVENTS
# =========================
def on_open(wsapp):
    global is_connected
    is_connected = True
    print("✅ WS Connected")


def on_message(wsapp, message):
    try:
        if isinstance(message, bytes):

            code = message[2]

            # 15 = LTP
            if code == 15:
                parse_ltp(message)

            # 23 = Depth
            elif code == 23:
                parse_depth(message)

        else:
            print("Text:", message)

    except Exception as e:
        print("Message error:", e)


def on_error(wsapp, error):
    print("❌ WS Error:", error)


def on_close(wsapp, close_status_code, close_msg):
    global is_connected
    is_connected = False
    print("❌ WS Closed")


# =========================
# START FEED
# =========================
def start_depth_feed():
    global ws

    token = get_token()
    if not token:
        print("❌ No token")
        return

    url = f"wss://api-feed.dhan.co?version=2&token={token}&clientId={CLIENT_ID}&authType=2"

    ws = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    thread = threading.Thread(target=ws.run_forever, daemon=True)
    thread.start()

    time.sleep(2)


# =========================
# SUBSCRIBE LTP
# =========================
def subscribe_ltp(security_id, segment):
    if not ws or not is_connected:
        print("WS not ready")
        return

    payload = {
        "RequestCode": 15,
        "InstrumentCount": 1,
        "InstrumentList": [
            {
                "ExchangeSegment": map_ws_segment(segment),
                "SecurityId": str(security_id)
            }
        ]
    }

    ws.send(json.dumps(payload))


# =========================
# SUBSCRIBE DEPTH
# =========================
def subscribe_depth(security_id, segment):
    if not ws or not is_connected:
        print("WS not ready")
        return

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

    ws.send(json.dumps(payload))


# =========================
# GETTERS
# =========================
def get_depth():
    return DEPTH_DATA


def get_ltp():
    return LTP_DATA
