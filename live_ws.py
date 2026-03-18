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
            data = json.loads(message)
            print("LIVE DATA:", data)   # debug
            self.latest_data = data
        except Exception as e:
            print("Parse Error:", e)

    def on_error(self, ws, error):
        print("ERROR:", error)

    def on_close(self, ws, close_status_code, close_msg):
        print("Connection Closed")

    def on_open(self, ws):
        print("Connected to Dhan WebSocket")

        # 🔥 FULL CORRECT PAYLOAD
        payload = {
            "RequestCode": 15,
            "InstrumentCount": 1,
            "InstrumentList": [
                {
                    "ExchangeSegment": 2,   # NSE_FNO
                    "SecurityId": 49081
                }
            ]
        }

        print("SENDING PAYLOAD:", payload)
        ws.send(json.dumps(payload))

    def start(self):
        self.ws = websocket.WebSocketApp(
            "wss://api-feed.dhan.co",
            header=[
                f"access-token: {self.access_token}",
                f"client-id: {self.client_id}"
            ],
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )

        thread = threading.Thread(target=self.ws.run_forever)
        thread.daemon = True
        thread.start()
