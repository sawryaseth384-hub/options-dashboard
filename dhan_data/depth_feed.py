import threading
import logging
from typing import Dict, List
from .websocket_manager import WebSocketManager
from .depth_parser import parse_depth_message
from .ltp_parser import parse_ltp_message

logger = logging.getLogger(__name__)

class DepthFeed:
    def __init__(self, token: str, client_id: str):
        self.ws_manager = WebSocketManager(token, client_id)
        self.ws_manager.set_message_callback(self._on_message)
        self.lock = threading.Lock()
        self.depth_data = {"bids": [], "asks": []}
        self.ltp = 0.0

    def _on_message(self, message: bytes):
        # Depth messages are longer, try depth first
        if len(message) >= 12 + 16 * 5:
            depth = parse_depth_message(message)
            if depth["bids"] or depth["asks"]:
                with self.lock:
                    self.depth_data = depth
                return
        # Otherwise try LTP
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
        payload = {
            "RequestCode": request_code,
            "InstrumentCount": 1,
            "InstrumentList": [
                {"ExchangeSegment": exchange_segment, "SecurityId": security_id}
            ]
        }
        return self.ws_manager.send(payload)

    def get_depth(self) -> Dict[str, List]:
        with self.lock:
            return {"bids": list(self.depth_data["bids"]), "asks": list(self.depth_data["asks"])}

    def get_ltp(self) -> float:
        with self.lock:
            return self.ltp


# Singleton and public functions
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
    feed.subscribe(1, security_id, segment)

def get_depth():
    return get_depth_feed().get_depth()

def get_ltp():
    return get_depth_feed().get_ltp()
