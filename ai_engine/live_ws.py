import websocket
import json
import threading

class DhanLive:

    def __init__(self, client_id, access_token):
        self.client_id = client_id
        self.access_token = access_token
        self.latest_data = {}

    def on_message(self, ws, message):
        try:
            self.latest_data = json.loads(message)
        except:
            pass

    def on_open(self, ws):
        payload = {
            "RequestCode": 15,
            "InstrumentCount": 1,
            "InstrumentList": [
                {
                    "ExchangeSegment": "NSE_FNO",
                    "SecurityId": "49081"
                }
            ]
        }
        ws.send(json.dumps(payload))

    def start(self):
        ws = websocket.WebSocketApp(
            "wss://api-feed.dhan.co",
            header=[
                f"access-token: {self.access_token}",
                f"client-id: {self.client_id}"
            ],
            on_message=self.on_message,
            on_open=self.on_open
        )

        thread = threading.Thread(target=ws.run_forever)
        thread.daemon = True
        thread.start()
