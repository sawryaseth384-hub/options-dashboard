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

DEPTH_DATA = {"bids": [], "asks": []}
LTP_DATA = 0


def map_ws_segment(segment):
    if segment == "NSE_FNO":
        return 2
    else:
        return 1


def parse_ltp(message):
    global LTP_DATA
    body = message[12:]
    ltp = struct.unpack('f', body[:4])[0]
    LTP_DATA = round(ltp, 2)


def parse_depth(message):
    global DEPTH_DATA

    body = message[12:]
    bids, asks = [], []

    for i in range(20):
        chunk = body[i*16:(i+1)*16]
        if len(chunk) < 16:
            continue

        price, qty, orders, side = struct.unpack('fiii', chunk)

        level = {"price": round(price, 2), "qty": qty}

        if side == 1:
            bids.append(level)
        else:
            asks.append(level)

    DEPTH_DATA = {"bids": bids, "asks": asks}


def on_open(wsapp):
    global is_connected
    is_connected = True


def on_message(wsapp, message):
    if isinstance(message, bytes):
        code = message[2]

        if code == 15:
            parse_ltp(message)

        elif code == 23:
            parse_depth(message)


def start_depth_feed():
    global ws

    token = get_token()

    url = f"wss://api-feed.dhan.co?version=2&token={token}&clientId={CLIENT_ID}&authType=2"

    ws = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message
    )

    threading.Thread(target=ws.run_forever, daemon=True).start()
    time.sleep(2)


def subscribe_ltp(security_id, segment):
    payload = {
        "RequestCode": 15,
        "InstrumentList": [{
            "ExchangeSegment": map_ws_segment(segment),
            "SecurityId": str(security_id)
        }]
    }
    ws.send(json.dumps(payload))


def subscribe_depth(security_id, segment):
    payload = {
        "RequestCode": 23,
        "InstrumentList": [{
            "ExchangeSegment": map_ws_segment(segment),
            "SecurityId": str(security_id)
        }]
    }
    ws.send(json.dumps(payload))


def get_ltp():
    return LTP_DATA


def get_depth():
    return DEPTH_DATA
