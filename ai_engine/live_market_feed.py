import websocket
import json
import threading
from utils.config import DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID

data_store = []

def on_message(ws, message):
    # Binary data आएगा → अभी raw store करो
    data_store.append(str(message))


def on_error(ws, error):
    data_store.append(f"ERROR: {error}")


def on_close(ws, close_status_code, close_msg):
    data_store.append("Connection Closed")


def on_open(ws):

    subscribe_msg = {
        "RequestCode": 15,
        "InstrumentCount": 1,
        "InstrumentList": [
            {
                "ExchangeSegment": "IDX_I",
                "SecurityId": "13"   # NIFTY
            }
        ]
    }

    ws.send(json.dumps(subscribe_msg))


def start_ws():

    url = f"wss://api-feed.dhan.co?version=2&token={DHAN_ACCESS_TOKEN}&clientId={DHAN_CLIENT_ID}&authType=2"

    ws = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    thread = threading.Thread(target=ws.run_forever)
    thread.daemon = True
    thread.start()


def get_live_market_feed():

    if not data_store:
        start_ws()

    return {
        "messages": data_store[-5:]   # last 5 messages
    }
