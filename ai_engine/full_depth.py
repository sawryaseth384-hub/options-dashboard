import websocket
import json
import struct
import threading
import time

from utils.config import ACCESS_TOKEN, CLIENT_ID

WS_URL = f"wss://depth-api-feed.dhan.co/twentydepth?token={ACCESS_TOKEN}&clientId={CLIENT_ID}&authType=2"


class FullMarketDepth:

    def __init__(self):
        self.ws = None
        self.depth_data = {
            "bids": [],
            "asks": []
        }

    # 🔹 ON OPEN
    def on_open(self, ws):
        print("✅ Connected to Depth Feed")

        subscribe = {
            "RequestCode": 23,
            "InstrumentCount": 1,
            "InstrumentList": [
                {
                    "ExchangeSegment": "NSE_FNO",
                    "SecurityId": "49081"
                }
            ]
        }

        ws.send(json.dumps(subscribe))
        print("📡 Subscribed")

    # 🔹 PARSE HEADER
    def parse_header(self, data):
        try:
            msg_len = struct.unpack('<H', data[0:2])[0]
            code = data[2]

            return code
        except:
            return None

    # 🔹 PARSE DEPTH
    def parse_depth(self, data):
        payload = data[12:]
        levels = []

        for i in range(0, len(payload), 16):
            chunk = payload[i:i+16]

            if len(chunk) < 16:
                continue

            price = struct.unpack('<d', chunk[0:8])[0]
            qty = struct.unpack('<I', chunk[8:12])[0]
            orders = struct.unpack('<I', chunk[12:16])[0]

            levels.append({
                "price": round(price, 2),
                "qty": qty,
                "orders": orders
            })

        return levels

    # 🔹 ON MESSAGE
    def on_message(self, ws, message):
        if isinstance(message, bytes):

            code = self.parse_header(message)

            depth = self.parse_depth(message)

            if not depth:
                return

            # 🔥 BID DATA
            if code == 41:
                self.depth_data["bids"] = depth

            # 🔥 ASK DATA
            elif code == 51:
                self.depth_data["asks"] = depth

            # 🔥 PRINT TOP LEVEL
            if self.depth_data["bids"] and self.depth_data["asks"]:
                print("\n📊 ORDER BOOK")

                print("🟢 TOP BIDS:", self.depth_data["bids"][:3])
                print("🔴 TOP ASKS:", self.depth_data["asks"][:3])

    # 🔹 ERROR
    def on_error(self, ws, error):
        print("❌ Error:", error)

    # 🔹 CLOSE
    def on_close(self, ws, close_status_code, close_msg):
        print("🔌 Closed")

    # 🔹 START
    def start(self):
        self.ws = websocket.WebSocketApp(
            WS_URL,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )

        thread = threading.Thread(target=self.ws.run_forever)
        thread.daemon = True
        thread.start()

        while True:
            time.sleep(1)

    # 🔥 GET DATA (IMPORTANT FOR DASHBOARD)
    def get_data(self):
        return self.depth_data
