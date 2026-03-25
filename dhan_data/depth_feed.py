class WebSocketManager:
    def __init__(self, token, client_id):
        self.token = token
        self.client_id = client_id
        self.ws = None
        self.is_connected = threading.Event()
        self._stop_flag = threading.Event()
        self._message_callback = None
        self._retry_count = 0
        self._max_retries = 3  # max retries

    def set_message_callback(self, callback):
        self._message_callback = callback

    def _on_open(self, ws):
        logger.info("WebSocket connected")
        self.is_connected.set()
        self._retry_count = 0

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
            logger.info(f"Reconnecting attempt {self._retry_count} in 30 seconds...")
            time.sleep(30)  # longer delay
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
