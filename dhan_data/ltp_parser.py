import struct
import logging

logger = logging.getLogger(__name__)

def parse_ltp_message(message: bytes):
    try:
        if len(message) >= 16:
            ltp = struct.unpack('<f', message[12:16])[0]
            return round(ltp, 2)
        return None
    except Exception as e:
        logger.debug(f"LTP parse error: {e}")
        return None
