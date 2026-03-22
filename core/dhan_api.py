# core/dhan_api.py
from dhan_data.instruments import get_symbol_data
from dhan_data.expiry import get_expiry
from dhan_data.historical_data import get_historical

def get_full_data(symbol):
    security_id, segment = get_symbol_data(symbol)
    if security_id is None:
        return {"error": "Symbol not found"}

    expiries = get_expiry(security_id, segment)
    historical = get_historical(security_id, segment)

    return {
        "symbol": symbol,
        "security_id": security_id,
        "segment": segment,
        "expiries": expiries,
        "historical": historical
    }
