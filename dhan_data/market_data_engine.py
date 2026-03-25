from datetime import datetime
import requests

from core.token_manager import get_headers
from dhan_data.expiry import get_expiry
from dhan_data.historical_data import get_historical
from dhan_data.instruments import get_symbol_data

BASE_URL = "https://api.dhan.co/v2"

INDEX_FALLBACK = {
    "NIFTY": (13, "IDX_I"),
    "BANKNIFTY": (25, "IDX_I"),
    "FINNIFTY": (27, "IDX_I"),
}

STOCK_FALLBACK = {
    "RELIANCE": (2885, "NSE_EQ"),
    "TCS": (11536, "NSE_EQ"),
    "INFY": (4083, "NSE_EQ"),
    "HDFCBANK": (1333, "NSE_EQ"),
    "ICICIBANK": (496, "NSE_EQ"),
    "SBIN": (3045, "NSE_EQ"),
}


def _post_json(headers, endpoint, payload):
    res = requests.post(
        f"{BASE_URL}/{endpoint}",
        headers=headers,
        json=payload,
        timeout=10,
    )
    if res.status_code != 200:
        return None
    try:
        return res.json()
    except ValueError:
        return None


def _resolve_symbols(symbols, fallback):
    resolved = {}
    for symbol in symbols:
        security_id, segment = get_symbol_data(symbol)
        if security_id is None:
            fallback_data = fallback.get(symbol)
            if fallback_data:
                security_id, segment = fallback_data
        if security_id and segment:
            resolved[symbol] = (int(security_id), segment)
    return resolved


def _normalize_quotes(quotes, instrument_map):
    normalized = []
    for item in quotes or []:
        security_id = item.get("securityId")
        segment = item.get("exchangeSegment")
        symbol = item.get("tradingSymbol") or item.get("symbol")
        if not symbol and security_id and segment:
            symbol = instrument_map.get((segment, int(security_id)))
        if not symbol:
            continue
        normalized.append({
            "symbol": symbol,
            "ltp": item.get("lastPrice") or item.get("ltp") or item.get("last_price"),
            "change_pct": item.get("changePercent") or item.get("pChange") or item.get("change_percentage"),
            "high": item.get("dayHigh") or item.get("high"),
            "low": item.get("dayLow") or item.get("low"),
        })
    return normalized


def _fetch_quotes(headers, symbols):
    instruments = []
    instrument_map = {}
    for symbol, (security_id, segment) in symbols.items():
        instruments.append({"exchangeSegment": segment, "securityId": int(security_id)})
        instrument_map[(segment, int(security_id))] = symbol
    if not instruments:
        return []
    payload = {"instruments": instruments}
    data = _post_json(headers, "marketquote", payload)
    if not data:
        return []
    return _normalize_quotes(data.get("data", []), instrument_map)


def _select_expiry(expiry_list):
    if isinstance(expiry_list, dict):
        expiry_list = expiry_list.get("data") or []
    if not expiry_list:
        return None
    first = expiry_list[0]
    if isinstance(first, dict):
        for key in ("expiry", "Expiry", "expiryDate", "date"):
            if key in first:
                return first[key]
    return first


def _calculate_pcr(chain):
    total_call = 0
    total_put = 0
    if not isinstance(chain, dict):
        return None
    for row in chain.values():
        call = row.get("ce") or row.get("CE") or {}
        put = row.get("pe") or row.get("PE") or {}
        total_call += float(call.get("oi") or 0)
        total_put += float(put.get("oi") or 0)
    if total_call == 0:
        return None
    return total_put / total_call


def _fetch_option_chain(headers, security_id, segment):
    expiry_list = get_expiry(security_id, segment)
    expiry = _select_expiry(expiry_list)
    if not expiry:
        return None
    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment,
        "Expiry": expiry,
    }
    data = _post_json(headers, "optionchain", payload)
    if not data or data.get("status") != "success":
        return None
    chain = data.get("data", {}).get("oc") or {}
    spot = data.get("data", {}).get("last_price") or data.get("data", {}).get("lastPrice")
    return {
        "oc": chain,
        "spot": spot,
        "pcr": _calculate_pcr(chain),
        "expiry": expiry,
    }


def _build_intraday(security_id, segment):
    data = get_historical(security_id, segment)
    if not data:
        return None
    closes = data.get("close") or []
    timestamps = data.get("timestamp") or []
    rows = []
    for ts, close in zip(timestamps, closes):
        rows.append({
            "timestamp": ts,
            "close": close,
        })
    return rows


def build_market_data():
    try:
        headers = get_headers()
    except Exception as exc:
        return {"_error": str(exc)}

    index_symbols = _resolve_symbols(["NIFTY", "BANKNIFTY", "FINNIFTY", "VIX"], INDEX_FALLBACK)
    stock_symbols = _resolve_symbols(
        ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN"],
        STOCK_FALLBACK,
    )

    indices = _fetch_quotes(headers, index_symbols)
    stocks = _fetch_quotes(headers, stock_symbols)

    nifty_id = index_symbols.get("NIFTY", INDEX_FALLBACK["NIFTY"])[0]
    options = _fetch_option_chain(headers, nifty_id, "IDX_I")
    intraday = _build_intraday(nifty_id, "IDX_I")

    return {
        "indices": indices,
        "global": [],
        "currency": [],
        "stocks": stocks,
        "options": options,
        "intraday": intraday,
        "last_updated": datetime.now().isoformat(timespec="seconds"),
    }
