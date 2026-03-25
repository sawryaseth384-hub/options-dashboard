from copy import deepcopy

from dhan_data.client import DhanApiClient
from dhan_data.instruments import get_symbol_data


DEFAULT_MARKET_DATA = {
    "indian": {
        "nifty": {},
        "banknifty": {},
        "finnifty": {},
        "vix": {},
    },
    "stocks": [],
    "options": {"chain": [], "pcr": 0},
}

INDEX_FALLBACKS = {
    "NIFTY": 13,
    "BANKNIFTY": 25,
    "FINNIFTY": 27,
}

STOCK_FALLBACKS = {
    "RELIANCE": 2885,
    "TCS": 11536,
    "HDFCBANK": 1333,
    "INFY": 4083,
    "ICICIBANK": 495,
}


def _to_float(value):
    try:
        return float(value)
    except Exception:
        return None


def _first_value(data, keys):
    if not isinstance(data, dict):
        return None
    for key in keys:
        if key in data:
            return data[key]
    return None


def _resolve_security_id(symbol, fallback=None):
    try:
        sec_id, _segment = get_symbol_data(symbol)
    except Exception:
        sec_id = None
    return sec_id or fallback


def _resolve_vix_id():
    for candidate in ("INDIAVIX", "INDIA VIX", "VIX"):
        sec_id = _resolve_security_id(candidate)
        if sec_id:
            return sec_id
    return None


def _unwrap_data(response):
    if response is None:
        return None
    if isinstance(response, dict):
        if response.get("status") == "success" and "data" in response:
            return response["data"]
        if "data" in response:
            return response["data"]
    return response


def _parse_quote_item(item):
    if not isinstance(item, dict):
        return None, None
    ltp = _first_value(item, ["lastPrice", "ltp", "last_price", "price", "LTP"])
    change_pct = _first_value(
        item,
        [
            "perChange",
            "changePercent",
            "change_percentage",
            "change_pct",
            "percentChange",
        ],
    )
    if change_pct is None:
        net_change = _first_value(item, ["netChange", "change", "net_change"])
        prev_close = _first_value(item, ["prevClose", "previousClose", "prev_close"])
        if net_change is not None and prev_close:
            change_pct = (_to_float(net_change) / _to_float(prev_close)) * 100
    return _to_float(ltp), _to_float(change_pct)


def _fetch_quotes(client, instruments):
    if not instruments:
        return {}
    payload = {
        "instruments": [
            {"exchangeSegment": instrument["segment"], "securityId": int(instrument["security_id"])}
            for instrument in instruments
            if instrument.get("security_id")
        ]
    }
    if not payload["instruments"]:
        return {}
    data, _error = client.post("marketquote", payload)
    items = _unwrap_data(data)
    if not isinstance(items, list):
        return {}
    quote_map = {}
    for item in items:
        sec_id = _first_value(item, ["securityId", "security_id"])
        if sec_id is None:
            continue
        quote_map[int(sec_id)] = item
    return quote_map


def _build_index_section(client):
    instruments = []
    index_specs = [
        ("NIFTY", INDEX_FALLBACKS.get("NIFTY"), "IDX_I"),
        ("BANKNIFTY", INDEX_FALLBACKS.get("BANKNIFTY"), "IDX_I"),
        ("FINNIFTY", INDEX_FALLBACKS.get("FINNIFTY"), "IDX_I"),
        ("VIX", _resolve_vix_id(), "IDX_I"),
    ]

    for symbol, fallback_id, segment in index_specs:
        sec_id = _resolve_security_id(symbol, fallback_id)
        instruments.append({"symbol": symbol, "security_id": sec_id, "segment": segment})

    quotes = _fetch_quotes(client, instruments)
    section = {}
    for instrument in instruments:
        symbol = instrument["symbol"]
        sec_id = instrument.get("security_id")
        quote = quotes.get(sec_id) if sec_id else None
        ltp, change_pct = _parse_quote_item(quote) if quote else (None, None)
        section[symbol.lower()] = {
            "symbol": symbol,
            "ltp": ltp,
            "change_pct": change_pct,
        }
    return section


def _build_stock_section(client):
    instruments = []
    for symbol, fallback_id in STOCK_FALLBACKS.items():
        sec_id = _resolve_security_id(symbol, fallback_id)
        if sec_id:
            instruments.append({"symbol": symbol, "security_id": sec_id, "segment": "NSE_EQ"})

    quotes = _fetch_quotes(client, instruments)
    stocks = []
    for instrument in instruments:
        symbol = instrument["symbol"]
        sec_id = instrument["security_id"]
        quote = quotes.get(sec_id) if sec_id else None
        ltp, change_pct = _parse_quote_item(quote) if quote else (None, None)
        high = _first_value(quote, ["dayHigh", "high", "day_high"]) if quote else None
        low = _first_value(quote, ["dayLow", "low", "day_low"]) if quote else None
        stocks.append(
            {
                "symbol": symbol,
                "ltp": ltp,
                "change_pct": change_pct,
                "high": _to_float(high),
                "low": _to_float(low),
            }
        )
    return stocks


def _fetch_expiry_list(client, security_id, segment):
    if not security_id:
        return []
    payload = {"UnderlyingScrip": int(security_id), "UnderlyingSeg": segment}
    data, _error = client.post("optionchain/expirylist", payload)
    data = _unwrap_data(data)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        return data["data"]
    return []


def _normalize_option_chain(chain):
    if not chain:
        return []
    rows = []
    if isinstance(chain, list):
        for row in chain:
            if not isinstance(row, dict):
                continue
            rows.append(
                {
                    "strike": _to_float(_first_value(row, ["strike", "Strike"])),
                    "call_oi": _to_float(_first_value(row, ["call_oi", "Call OI", "ce_oi"])),
                    "put_oi": _to_float(_first_value(row, ["put_oi", "Put OI", "pe_oi"])),
                    "call_ltp": _to_float(_first_value(row, ["call_ltp", "Call LTP", "ce_ltp"])),
                    "put_ltp": _to_float(_first_value(row, ["put_ltp", "Put LTP", "pe_ltp"])),
                }
            )
        return rows

    if isinstance(chain, dict):
        for strike, payload in chain.items():
            if not isinstance(payload, dict):
                continue
            call = payload.get("ce") or payload.get("CE") or payload.get("call") or {}
            put = payload.get("pe") or payload.get("PE") or payload.get("put") or {}
            rows.append(
                {
                    "strike": _to_float(strike),
                    "call_oi": _to_float(_first_value(call, ["oi", "open_interest"])),
                    "put_oi": _to_float(_first_value(put, ["oi", "open_interest"])),
                    "call_ltp": _to_float(_first_value(call, ["last_price", "ltp"])),
                    "put_ltp": _to_float(_first_value(put, ["last_price", "ltp"])),
                }
            )
    return rows


def _build_options_section(client):
    security_id = INDEX_FALLBACKS.get("NIFTY")
    segment = "IDX_I"
    expiries = _fetch_expiry_list(client, security_id, segment)
    if not expiries:
        return {"chain": [], "pcr": 0}

    expiry = expiries[0]
    payload = {"UnderlyingScrip": int(security_id), "UnderlyingSeg": segment, "Expiry": expiry}
    data, _error = client.post("optionchain", payload)
    data = _unwrap_data(data)
    if not isinstance(data, dict):
        return {"chain": [], "pcr": 0}

    chain = data.get("oc") or data.get("records") or data.get("option_chain")
    spot = _first_value(data, ["last_price", "spot", "underlying_ltp", "ltp"])
    rows = _normalize_option_chain(chain)
    total_call = sum([row.get("call_oi") or 0 for row in rows])
    total_put = sum([row.get("put_oi") or 0 for row in rows])
    pcr = (total_put / total_call) if total_call else 0

    return {"chain": rows, "pcr": pcr, "spot": _to_float(spot), "expiry": expiry}


def build_market_data():
    market_data = deepcopy(DEFAULT_MARKET_DATA)
    client = DhanApiClient()

    try:
        market_data["indian"] = _build_index_section(client)
    except Exception:
        market_data["indian"] = deepcopy(DEFAULT_MARKET_DATA["indian"])

    try:
        market_data["stocks"] = _build_stock_section(client)
    except Exception:
        market_data["stocks"] = []

    try:
        market_data["options"] = _build_options_section(client)
    except Exception:
        market_data["options"] = {"chain": [], "pcr": 0}

    return market_data
