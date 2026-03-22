# core/dhan_api.py
from dhan_data.instruments import get_symbol_data
from dhan_data.expiry import get_expiry
from dhan_data.historical_data import get_historical

def get_full_data(symbol):
    """Fetch all data for a symbol: security ID, segment, expiries, historical candles."""
    security_id, segment = get_symbol_data(symbol)
    if security_id is None:
        return {"error": "Symbol not found"}

    # Get expiry list using the correct segment (original segment from instrument data)
    expiries = get_expiry(security_id, segment)

    # Get historical intraday data (5‑minute candles)
    historical = get_historical(security_id, segment)

    return {
        "symbol": symbol,
        "security_id": security_id,
        "segment": segment,
        "expiries": expiries,
        "historical": historical
    }
