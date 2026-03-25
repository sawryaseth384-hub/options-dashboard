import json
import threading
import time
import websocket
import logging

logging.basicConfig(level=logging.INFO)

class DepthFeed:
    def __init__(self, token, client_id):
        self.token = token
        self.client_id = client_id
        self.ws = None
        self.connected = False
        self.depth_data = {"bids": [], "asks": []}

    # =========================
    # ON MESSAGE
    # =========================
    def on_message(self, ws, message):
        try:
            data = json.loads(message)

            if "Depth" in data:
                self.depth_data = data["Depth"]
                logging.info("📊 Depth Updated")

        except Exception as e:
            logging.error(f"Parse Error: {e}")

    # =========================
    # EVENTS
    # =========================
    def on_open(self, ws):
        self.connected = True
        logging.info("✅ WebSocket Connected")

    def on_close(self, ws, a, b):
        self.connected = False
        logging.info("❌ WebSocket Closed")

    def on_error(self, ws, error):
        logging.error(f"WS Error: {error}")

    # =========================
    # START CONNECTION
    # =========================
    def start(self):
        url = f"wss://api-feed.dhan.co?version=2&token={self.token}&clientId={self.client_id}&authType=2"

        self.ws = websocket.WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_close=self.on_close,
            on_error=self.on_error
        )

        thread = threading.Thread(target=self.ws.run_forever)
        thread.daemon = True
        thread.start()

        # wait for connection
        timeout = 10
        start = time.time()
        while not self.connected and time.time() - start < timeout:
            time.sleep(0
