import struct
import logging

logger = logging.getLogger(__name__)

def parse_depth_message(message: bytes):
    try:
        if len(message) < 12:
            return {"bids": [], "asks": []}
        body = message[12:]

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
