import websocket
import json
import threading
import time
from utils.config import ACCESS_TOKEN, CLIENT_ID

# 🔥 WEBSOCKET URL
WS_URL = f"wss://api-feed.dhan.co?version=2&token={ACCESS_TOKEN}&clientId={CLIENT_ID}&authType=2"


class LiveMarketFeed:

    def __init__(self):
        self.ws = None

    # 🔹 ON OPEN
    def on_open(self, ws):
        print("✅ Connected to Dhan WebSocket")

        # 🔥 SUBSCRIBE INSTRUMENT
        subscribe_message = {
            "RequestCode": 15,
            "InstrumentCount": 1,
            "InstrumentList": [
                {
                    "ExchangeSegment": "NSE_FNO",
                    "SecurityId": "49081"
                }
            ]
        }

        ws.send(json.dumps(subscribe_message))
        print("📡 Subscribed to instruments")

    # 🔹 ON MESSAGE
    def on_message(self, ws, message):
        print("📊 RAW DATA:", message)

        # ⚠️ NOTE:
        # Ye binary data hai → yaha parse karna padega (advanced step)
        # Abhi raw print kar rahe hain

    # 🔹 ON ERROR
    def on_error(self, ws, error):
        print("❌ Error:", error)

    # 🔹 ON CLOSE
    def on_close(self, ws, close_status_code, close_msg):
        print("🔌 Connection Closed")

    # 🔹 START CONNECTION
    def start(self):
        self.ws = websocket.WebSocketApp(
            WS_URL,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )

        # 🔥 THREAD ME RUN (IMPORTANT)
        thread = threading.Thread(target=self.ws.run_forever)
        thread.daemon = True
        thread.start()

        # Keep running
        while True:
            time.sleep(1)
