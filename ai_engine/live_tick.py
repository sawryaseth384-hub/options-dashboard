import websocket
import json
import struct
import threading

from utils.config import ACCESS_TOKEN, CLIENT_ID


WS_URL = f"wss://api-feed.dhan.co?version=2&token={ACCESS_TOKEN}&clientId={CLIENT_ID}&authType=2"


class LiveTick:

    def __init__(self):
        self.ws = None

    def on_open(self, ws):
        print("✅ Tick Connected")

        subscribe = {
            "RequestCode": 19,  # 🔥 FULL PACKET (Tick-by-Tick)
            "InstrumentCount": 1,
            "InstrumentList": [
                {
                    "ExchangeSegment": "NSE_FNO",
                    "SecurityId": "49081"
                }
            ]
        }

        ws.send(json.dumps(subscribe))

    def on_message(self, ws, message):

        if isinstance(message, bytes):

            try:
                # 🔥 BASIC DATA
                ltp = struct.unpack('<f', message[8:12])[0]
                volume = struct.unpack('<i', message[22:26])[0]
                sell_qty = struct.unpack('<i', message[26:30])[0]
                buy_qty = struct.unpack('<i', message[30:34])[0]

                # 🔥 OI DATA
                oi = struct.unpack('<i', message[34:38])[0]

                # 🔥 OHLC
                open_p = struct.unpack('<f', message[46:50])[0]
                high = struct.unpack('<f', message[54:58])[0]
                low = struct.unpack('<f', message[58:62])[0]

                # 🔥 DEPTH (5 LEVEL)
                depth_start = 62
                depth = []

                for i in range(5):
                    base = depth_start + (i * 20)

                    bid_qty = struct.unpack('<i', message[base:base+4])[0]
                    ask_qty = struct.unpack('<i', message[base+4:base+8])[0]
                    bid_price = struct.unpack('<f', message[base+12:base+16])[0]
                    ask_price = struct.unpack('<f', message[base+16:base+20])[0]

                    depth.append({
                        "bid_price": bid_price,
                        "bid_qty": bid_qty,
                        "ask_price": ask_price,
                        "ask_qty": ask_qty
                    })

                print({
                    "ltp": round(ltp, 2),
                    "oi": oi,
                    "volume": volume,
                    "buy_qty": buy_qty,
                    "sell_qty": sell_qty,
                    "depth": depth[0]  # 🔥 top level
                })

            except Exception as e:
                print("Parse Error:", e)

    def on_error(self, ws, error):
        print("❌ Error:", error)

    def on_close(self, ws, close_status_code, close_msg):
        print("🔌 Closed")

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
