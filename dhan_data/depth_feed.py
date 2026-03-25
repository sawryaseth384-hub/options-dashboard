import json
import threading
import struct
import time
import logging
import websocket
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DepthFeed:
    """Manages WebSocket connection for Dhan market depth and LTP."""

    def __init__(self, token: str, client_id: str):
        self.token = token
        self.client_id = client_id
        self.ws: Optional[websocket.WebSocketApp] = None
        self.is_connected = threading.Event()
        self.lock = threading.Lock()
        self.depth_data = {"bids": [], "asks": []}
        self.ltp_data = {"ltp": 0.0, "symbol": "", "timestamp": 0}
        self._stop_flag = threading.Event()

    def _on_message(self, ws, message):
        if isinstance(message, bytes):
            # Check message type (first few bytes may indicate type)
            # For now assume it's depth or LTP based on length or header
            self._parse_message(message)

    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.is_connected.clear()
        if not self._stop_flag.is_set():
            self._reconnect()

    def _on_open(self, ws):
        logger.info("WebSocket connected")
        self.is_connected.set()

    def _parse_message(self, message: bytes):
        """Parse binary message based on Dhan protocol.
        We'll try to detect depth (20 levels) vs LTP (smaller message).
        For simplicity, assume depth messages have at least 12+16*20 bytes.
        LTP messages might be shorter. You may need to adjust based on actual header.
        """
        try:
            if len(message) < 12:
                return
            # Assume first 2 bytes indicate message type (might be header)
            # For now we try depth parsing first, if fails fallback to LTP
            # Actually, depth messages have a specific pattern.
            # We'll parse based on length: depth messages are longer.
            if len(message) >= 12 + 16 * 5:  # at least 5 levels
                self._parse_depth(message)
            else:
                self._parse_ltp(message)
        except Exception as e:
            logger.exception("Error parsing message")

    def _parse_depth(self, message: bytes):
        """Parse binary depth message (20 levels)."""
        body = message[12:]  # skip header (adjust if needed)
        bids = []
        asks = []
        entry_size = 16
        expected_entries = 20
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
            except struct.error:
                continue

            entry = {"price": round(price, 2), "qty": qty, "orders": orders}
            if side == 1:  # bid
                bids.append(entry)
            else:          # ask
                asks.append(entry)

        bids.sort(key=lambda x: x['price'], reverse=True)
        asks.sort(key=lambda x: x['price'])

        with self.lock:
            self.depth_data = {"bids": bids, "asks": asks}

    def _parse_ltp(self, message: bytes):
        """Parse LTP message (likely contains price)."""
        # This is a placeholder – you need actual Dhan LTP binary format.
        # Usually LTP messages are small; might have price at specific offset.
        # For now, try to extract a float from somewhere.
        # Better: check Dhan documentation for LTP packet format.
        try:
            # Example: LTP might be at offset 12-16 as float
            if len(message) >= 16:
                ltp = struct.unpack('<f', message[12:16])[0]
                with self.lock:
                    self.ltp_data = {"ltp": round(ltp, 2), "symbol": "", "timestamp": time.time()}
        except Exception:
            pass

    def _reconnect(self):
        if self._stop_flag.is_set():
            return
        logger.info("Reconnecting in 5 seconds...")
        time.sleep(5)
        self.start()

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

    def subscribe(self, request_code: int, security_id: int, segment: str):
        """Generic subscription."""
        if not self.is_connected.is_set():
            logger.error("WebSocket not connected")
            return False

        segment_map = {"NSE_EQ": 1, "NSE_FNO": 2, "BSE_EQ": 3, "NSE_IDX": 4}
        exchange_segment = segment_map.get(segment, 1)
        payload = {
            "RequestCode": request_code,
            "InstrumentCount": 1,
            "InstrumentList": [
                {"ExchangeSegment": exchange_segment, "SecurityId": security_id}
            ]
        }
        try:
            self.ws.send(json.dumps(payload))
            logger.info(f"Subscribed request {request_code} for {security_id} ({segment})")
            return True
        except Exception as e:
            logger.error(f"Subscription failed: {e}")
            return False

    def get_depth(self) -> Dict[str, List]:
        with self.lock:
            return {"bids": list(self.depth_data["bids"]), "asks": list(self.depth_data["asks"])}

    def get_ltp(self) -> float:
        with self.lock:
            return self.ltp_data.get("ltp", 0.0)


# ------------------------------------------------------------------
# Global instance for Streamlit (cached)
# ------------------------------------------------------------------
_depth_feed_instance = None

def get_depth_feed():
    """Return singleton DepthFeed instance. Must be called after token is available."""
    global _depth_feed_instance
    if _depth_feed_instance is None:
        # Import these only when needed to avoid circular imports
        from core.token_manager import get_token
        import streamlit as st
        token = get_token()
        client_id = st.secrets["CLIENT_ID"]
        _depth_feed_instance = DepthFeed(token, client_id)
        _depth_feed_instance.start()
    return _depth_feed_instance


# ------------------------------------------------------------------
# Public API functions expected by app.py
# ------------------------------------------------------------------
def start_depth_feed():
    """Start depth feed (idempotent)."""
    feed = get_depth_feed()
    # Already started by get_depth_feed, but we ensure it's running
    if not feed.is_connected.is_set():
        feed.start()

def subscribe_depth(security_id, segment):
    """Subscribe to market depth for given instrument."""
    feed = get_depth_feed()
    # Depth subscription uses RequestCode 23 (as per your earlier code)
    feed.subscribe(23, security_id, segment)

def subscribe_ltp(security_id, segment):
    """Subscribe to LTP (last traded price) for given instrument."""
    feed = get_depth_feed()
    # LTP subscription uses RequestCode 1 (common for market data)
    feed.subscribe(1, security_id, segment)

def get_depth():
    """Return current depth data."""
    feed = get_depth_feed()
    return feed.get_depth()

def get_ltp():
    """Return current LTP."""
    feed = get_depth_feed()
    return feed.get_ltp()
