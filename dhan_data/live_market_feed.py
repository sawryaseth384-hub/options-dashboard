import websocket
import json
import threading

WS_URL = "wss://api-feed.dhan.co"

ws = None
latest_data = {}


def start_feed(token, client_id):

    global ws

    url = f"{WS_URL}?version=2&token={token}&clientId={client_id}&authType=2"

    def on_message(ws, message):
        global latest_data
        latest_data = message
        print("LIVE:", message)

    def on_open(ws):
        print("Connected")

        sub_msg = {
            "RequestCode": 15,
            "InstrumentCount": 1,
            "InstrumentList": [
                {
                    "ExchangeSegment": "NSE_EQ",
                    "SecurityId": "2885"
                }
            ]
        }

        ws.send(json.dumps(sub_msg))

    ws = websocket.WebSocketApp(
        url,
        on_message=on_message,
        on_open=on_open
    )

    thread = threading.Thread(target=ws.run_forever)
    thread.start()


def get_live_data():
    return latest_data
