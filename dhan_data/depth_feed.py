import json
import threading
import struct
import time
import logging
import websocket
from typing import Dict, List, Optional

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DepthFeed:
    """Manages WebSocket connection for Dhan market depth."""

    def __init__(self, token: str, client_id: str):
        self.token = token
        self.client_id = client_id
        self.ws: Optional[websocket.WebSocketApp] = None
        self.is_connected = threading.Event()
        self.lock = threading.Lock()
        self.depth_data = {"bids": [], "asks": []}
        self._stop_flag = threading.Event()

    def _on_message(self, ws, message):
        if isinstance(message, bytes):
            self._parse_depth(message)

    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.is_connected.clear()
        # Auto reconnect if not stopped manually
        if not self._stop_flag.is_set():
            self._reconnect()

    def _on_open(self, ws):
        logger.info("WebSocket connected")
        self.is_connected.set()

    def _parse_depth(self, message: bytes):
        """Parse binary depth message from Dhan."""
        try:
            # Skip first 12 bytes (header) – adjust if format changes
            if len(message) < 12:
                logger.warning("Message too short for header")
                return
            body = message[12:]

            bids = []
            asks = []
            entry_size = 16
            expected_entries = 20   # Dhan sends max 20 levels
            for i in range(expected_entries):
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
                except struct.error as e:
                    logger.error(f"Struct unpack error at entry {i}: {e}")
                    continue

                entry = {
                    "price": round(price, 2),
                    "qty": qty,
                    "orders": orders
                }
                if side == 1:   # 1 = bid
                    bids.append(entry)
                else:           # ask
                    asks.append(entry)

            # Sort bids descending, asks ascending (optional but good)
            bids.sort(key=lambda x: x['price'], reverse=True)
            asks.sort(key=lambda x: x['price'])

            with self.lock:
                self.depth_data = {"bids": bids, "asks": asks}
        except Exception as e:
            logger.exception("Error parsing depth message")

    def _reconnect(self):
        """Attempt to reconnect after delay."""
        if self._stop_flag.is_set():
            return
        logger.info("Reconnecting in 5 seconds...")
        time.sleep(5)
        self.start()

    def start(self):
        """Start WebSocket connection."""
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

        # Wait for connection (max 10 sec)
        if not self.is_connected.wait(timeout=10):
            logger.error("Failed to connect within timeout")

    def stop(self):
        """Gracefully stop WebSocket."""
        self._stop_flag.set()
        if self.ws:
            self.ws.close()
        if hasattr(self, 'ws_thread') and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=2)

    def subscribe_depth(self, security_id: int, segment: str):
        """Subscribe to depth for a given instrument."""
        if not self.is_connected.is_set():
            logger.error("WebSocket not connected")
            return

        # Map segment to exchange code
        segment_map = {
            "NSE_EQ": 1,
            "NSE_FNO": 2,
            "BSE_EQ": 3,
            "NSE_IDX": 4,   # if supported
        }
        exchange_segment = segment_map.get(segment, 1)
        if exchange_segment == 1 and segment not in segment_map:
            logger.warning(f"Unknown segment '{segment}', defaulting to NSE_EQ")

        payload = {
            "RequestCode": 23,
            "InstrumentCount": 1,
            "InstrumentList": [
                {
                    "ExchangeSegment": exchange_segment,
                    "SecurityId": security_id   # integer expected
                }
            ]
        }

        try:
            self.ws.send(json.dumps(payload))
            logger.info(f"Subscribed to depth for {security_id} ({segment})")
        except Exception as e:
            logger.error(f"Failed to send subscription: {e}")

    def get_depth(self) -> Dict[str, List]:
        """Thread-safe retrieval of current depth data."""
        with self.lock:
            # Return a copy to avoid external modifications
            return {
                "bids": list(self.depth_data["bids"]),
                "asks": list(self.depth_data["asks"])
            }
