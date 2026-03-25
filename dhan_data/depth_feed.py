import json
import threading
import struct
import time
import logging
import websocket

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# WebSocket Manager with Exponential Backoff
# ------------------------------------------------------------------
class WebSocketManager:
    def __init__(self, token, client_id):
        self.token = token
        self.client_id = client_id
        self.ws = None
        self.is_connected = threading.Event()
        self._stop_flag = threading.Event()
        self._message_callback = None
        self._retry_count = 0
        self._max_retries = 3
        self._retry_delay = 5   # initial delay in seconds

    def set_message_callback(self, callback):
        self._message_callback = callback

    def _on_open(self, ws):
        logger.info("WebSocket connected")
        self.is_connected.set()
        self._retry_count = 0
        self._retry_delay = 5

    def _on_message(self, ws, message):
        if self._message_callback and isinstance(message, bytes):
            self._message_callback(message)

    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.is_connected.clear()
        if not self._stop_flag.is_set() and self._retry_count < self._max_retries:
            self._retry_count += 1
            delay = self._retry_delay * (2 ** (self._retry_count - 1))  # exponential backoff
            logger.info(f"Reconnecting attempt {self._retry_count} in {delay} seconds...")
            time.sleep(delay)
            self.start()
        elif self._retry_count >= self._max_retries:
            logger.error("Max retries reached. Stopping reconnection.")

    def start(self):
        if self._stop_flag.is_set():
            self._stop_flag.clear()
        url = f"wss://api-feed.dhan.co?version=2&token={self.token}&clientId={self.client_id}&authType=2"
        self.ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self.ws_thread.start()
        if not self.is_connected.wait(timeout=10):
            logger.error("Failed to connect within timeout")

    def stop(self):
        self._stop_flag.set()
        if self.ws:
            self.ws.close()
        if hasattr(self, 'ws_thread') and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=2)

    def send(self, data):
        if not self.is_connected.is_set():
            logger.error("WebSocket not connected")
            return False
        try:
            self.ws.send(json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Send failed: {e}")
            return False

# ------------------------------------------------------------------
# Depth Parser
# ------------------------------------------------------------------
def parse_depth_message(message: bytes):
    try:
        if len(message) < 12:
            return {"bids": [], "asks": []}
        body = message[12:]   # skip header (8 bytes? docs say 8? but we keep 12)
        bids, asks = [], []
        entry_size = 16
        for i in range(20):
            start = i * entry_size
            end = start + entry_size
            if end > len(body):
                break
            chunk = body[start:end]
            try:
                price = struct.unpack('<f', chunk[0:4])[0]
                qty = struct.unpack('<i', chunk[4:8])[0]
                orders = struct.unpack('<i', chunk[8:12])[0]
                side = struct.unpack('<i', chunk[12:16])[0]
            except struct.error:
                continue
            entry = {"price": round(price, 2), "qty": qty, "orders": orders}
            if side == 1:
                bids.append(entry)
            else:
                asks.append(entry)
        bids.sort(key=lambda x: x['price'], reverse=True)
        asks.sort(key=lambda x: x['price'])
        return {"bids": bids, "asks": asks}
    except Exception as e:
        logger.exception("Error parsing depth")
        return {"bids": [], "asks": []}

# ------------------------------------------------------------------
# LTP Parser (based on Ticker packet)
# ------------------------------------------------------------------
def parse_ltp_message(message: bytes):
    try:
        # According to Dhan docs, LTP is in Ticker packet (request_code=2)
        # The header is 8 bytes, then LTP as float at bytes 9-12.
        if len(message) >= 12:
            ltp = struct.unpack('<f', message[8:12])[0]   # offset 8-12
            return round(ltp, 2)
        return None
    except Exception as e:
        logger.debug(f"LTP parse error: {e}")
        return None

# ------------------------------------------------------------------
# Main DepthFeed Class
# ------------------------------------------------------------------
class DepthFeed:
    def __init__(self, token: str, client_id: str):
        self.ws_manager = WebSocketManager(token, client_id)
        self.ws_manager.set_message_callback(self._on_message)
        self.lock = threading.Lock()
        self.depth_data = {"bids": [], "asks": []}
        self.ltp = 0.0

    def _on_message(self, message: bytes):
        # Depth messages are longer (full packet)
        if len(message) >= 12 + 16 * 5:
            depth = parse_depth_message(message)
            if depth["bids"] or depth["asks"]:
                with self.lock:
                    self.depth_data = depth
                return
        # Otherwise try LTP (ticker packet)
        ltp_val = parse_ltp_message(message)
        if ltp_val is not None:
            with self.lock:
                self.ltp = ltp_val

    def start(self):
        self.ws_manager.start()

    def stop(self):
        self.ws_manager.stop()

    def subscribe(self, request_code: int, security_id: int, segment: str) -> bool:
        segment_map = {"NSE_EQ": 1, "NSE_FNO": 2, "BSE_EQ": 3, "NSE_IDX": 4}
        exchange_segment = segment_map.get(segment, 1)
        if request_code == 23 and segment in ["IDX_I", "NSE_IDX"]:
            logger.warning(f"Index depth not supported for {segment}")
            return False
        payload = {
            "RequestCode": request_code,
            "InstrumentCount": 1,
            "InstrumentList": [
                {"ExchangeSegment": exchange_segment, "SecurityId": security_id}
            ]
        }
        return self.ws_manager.send(payload)

    def get_depth(self):
        with self.lock:
            return {"bids": list(self.depth_data["bids"]), "asks": list(self.depth_data["asks"])}

    def get_ltp(self):
        with self.lock:
            return self.ltp

# ------------------------------------------------------------------
# Singleton & Public API (as expected by app.py)
# ------------------------------------------------------------------
_depth_feed_instance = None

def get_depth_feed():
    global _depth_feed_instance
    if _depth_feed_instance is None:
        from core.token_manager import get_token
        import streamlit as st
        token = get_token()
        client_id = st.secrets["CLIENT_ID"]
        _depth_feed_instance = DepthFeed(token, client_id)
        _depth_feed_instance.start()
    return _depth_feed_instance

def start_depth_feed():
    feed = get_depth_feed()
    if not feed.ws_manager.is_connected.is_set():
        feed.start()

def subscribe_depth(security_id, segment):
    feed = get_depth_feed()
    feed.subscribe(23, security_id, segment)

def subscribe_ltp(security_id, segment):
    feed = get_depth_feed()
    feed.subscribe(1, security_id, segment)   # request code 1 = Ticker (LTP)

def get_depth():
    return get_depth_feed().get_depth()

def get_ltp():
    return get_depth_feed().get_ltp()
