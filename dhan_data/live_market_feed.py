import websocket
import json
import threading

ltp_data = {}

def on_message(ws, message):
    global ltp_data
    data = json.loads(message)
    ltp_data = data

def on_open(ws):
    print("Connected to Dhan Live Feed")

def start_live_feed(token, client_id):
    url = f"wss://api-feed.dhan.co?version=2&token={token}&clientId={client_id}&authType=2"

    ws = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message
    )

    thread = threading.Thread(target=ws.run_forever)
    thread.daemon = True
    thread.start()

def get_live_ltp():
    return ltp_data
