from dhan_data.client import DhanApiClient
from dhan_data.instruments import get_symbol_data


DEFAULT_INDEXES = {
    "NIFTY": {"security_id": 13, "segment": "IDX_I"},
    "BANKNIFTY": {"security_id": 25, "segment": "IDX_I"},
    "FINNIFTY": {"security_id": 27, "segment": "IDX_I"},
}

DEFAULT_STOCKS = [
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "SBIN",
    "ITC",
    "LT",
]

VIX_ALIASES = ["INDIAVIX", "VIX"]


def _as_float(value):
    try:
        return float(value)
    except Exception:
        return None


def _resolve_symbol(symbol, fallback_security_id=None, fallback_segment=None, aliases=None):
    candidates = [symbol]
    if aliases:
        candidates.extend([alias for alias in aliases if alias not in candidates])
    for candidate in candidates:
        security_id, segment = get_symbol_data(candidate)
        if security_id and segment:
            return int(security_id), segment
    if fallback_security_id and fallback_segment:
        return int(fallback_security_id), fallback_segment
    return None, None


def _extract_quote_values(item):
    if not isinstance(item, dict):
        return None, None
    ltp = item.get("lastPrice") or item.get("ltp") or item.get("last_price") or item.get("price")
    change_pct = (
        item.get("changePercent")
        or item.get("change_percent")
        or item.get("changePercentage")
        or item.get("pChange")
        or item.get("pctChange")
    )
    if change_pct is None:
        change = item.get("change") or item.get("absChange") or item.get("changeValue")
        prev = item.get("previousClose") or item.get("prevClose") or item.get("previous_close")
        if change is not None and prev:
            try:
                change_pct = (float(change) / float(prev)) * 100
            except Exception:
                change_pct = None
    return ltp, change_pct


def _fetch_market_quotes(client, instruments):
    if not instruments:
        return {}
    payload = {
        "instruments": [
            {"exchangeSegment": segment, "securityId": int(security_id)}
            for security_id, segment in instruments
        ]
    }
    data, _ = client.post("/marketquote", payload)
    items = []
    if isinstance(data, dict):
        items = data.get("data") or data.get("Data") or []
    if not isinstance(items, list):
        return {}
    quote_map = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        security_id = item.get("securityId") or item.get("security_id")
        if security_id is None:
            continue
        quote_map[str(security_id)] = item
    return quote_map


def _get_expiry_list(client, underlying_scrip, segment):
    payload = {"UnderlyingScrip": int(underlying_scrip), "UnderlyingSeg": segment}
    data, _ = client.post("/optionchain/expirylist", payload)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        expiries = data.get("data") or []
        if isinstance(expiries, list):
            return expiries
    return []


def _normalize_option_chain(data):
    if not data:
        return [], None
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    spot = None
    if isinstance(data, dict):
        spot = data.get("last_price") or data.get("spot_price") or data.get("underlying_value")
    chain = None
    if isinstance(data, dict):
        chain = data.get("oc") or data.get("records") or data.get("chain")
    if chain is None:
        chain = data if isinstance(data, (list, dict)) else None
    if chain is None:
        return [], spot

    rows = []
    if isinstance(chain, dict):
        for strike, entry in chain.items():
            if not isinstance(entry, dict):
                continue
            call = entry.get("ce") or entry.get("CE") or {}
            put = entry.get("pe") or entry.get("PE") or {}
            rows.append({
                "strike": _as_float(strike),
                "call_oi": call.get("oi"),
                "put_oi": put.get("oi"),
                "call_ltp": call.get("ltp") or call.get("last_price"),
                "put_ltp": put.get("ltp") or put.get("last_price"),
                "CE": call,
                "PE": put,
            })
    elif isinstance(chain, list):
        for entry in chain:
            if not isinstance(entry, dict):
                continue
            strike = entry.get("strike") or entry.get("strikePrice") or entry.get("Strike")
            call = entry.get("ce") or entry.get("CE") or entry.get("call") or {}
            put = entry.get("pe") or entry.get("PE") or entry.get("put") or {}
            rows.append({
                "strike": _as_float(strike),
                "call_oi": entry.get("call_oi") or call.get("oi"),
                "put_oi": entry.get("put_oi") or put.get("oi"),
                "call_ltp": entry.get("call_ltp") or call.get("ltp") or call.get("last_price"),
                "put_ltp": entry.get("put_ltp") or put.get("ltp") or put.get("last_price"),
                "CE": call,
                "PE": put,
            })
    return rows, spot


def build_market_data():
    market_data = {
        "indian": {"nifty": {}, "banknifty": {}, "finnifty": {}, "vix": {}},
        "stocks": [],
        "options": {"chain": [], "pcr": 0},
    }

    try:
        client = DhanApiClient()

        index_instruments = []
        index_lookup = {}
        for symbol, fallback in DEFAULT_INDEXES.items():
            security_id, segment = _resolve_symbol(
                symbol,
                fallback_security_id=fallback["security_id"],
                fallback_segment=fallback["segment"],
            )
            if security_id and segment:
                index_instruments.append((security_id, segment))
                index_lookup[str(security_id)] = symbol

        vix_security_id, vix_segment = _resolve_symbol(
            "VIX",
            fallback_security_id=None,
            fallback_segment=None,
            aliases=VIX_ALIASES,
        )
        if vix_security_id and vix_segment:
            index_instruments.append((vix_security_id, vix_segment))
            index_lookup[str(vix_security_id)] = "VIX"

        quote_map = _fetch_market_quotes(client, index_instruments)
        indian_section = {}
        for symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "VIX"]:
            item = None
            for security_id, name in index_lookup.items():
                if name == symbol:
                    item = quote_map.get(security_id)
                    break
            ltp, change_pct = _extract_quote_values(item)
            indian_section[symbol.lower()] = {"symbol": symbol, "ltp": ltp, "change_pct": change_pct}
        market_data["indian"] = indian_section

        stock_instruments = []
        stock_lookup = {}
        for symbol in DEFAULT_STOCKS:
            security_id, segment = _resolve_symbol(symbol, fallback_security_id=None, fallback_segment="NSE_EQ")
            if security_id and segment:
                stock_instruments.append((security_id, segment))
                stock_lookup[str(security_id)] = symbol

        stock_quotes = _fetch_market_quotes(client, stock_instruments)
        stocks = []
        for security_id, symbol in stock_lookup.items():
            item = stock_quotes.get(security_id)
            ltp, change_pct = _extract_quote_values(item)
            stocks.append({"symbol": symbol, "ltp": ltp, "change_pct": change_pct})
        market_data["stocks"] = stocks

        underlying_id = DEFAULT_INDEXES["NIFTY"]["security_id"]
        expiries = _get_expiry_list(client, underlying_id, "IDX_I")
        expiry = expiries[0] if expiries else None
        option_chain_rows = []
        spot_price = None
        if expiry:
            payload = {"UnderlyingScrip": int(underlying_id), "UnderlyingSeg": "IDX_I", "Expiry": expiry}
            data, _ = client.post("/optionchain", payload)
            option_chain_rows, spot_price = _normalize_option_chain(data)

        total_call = sum([_as_float(row.get("call_oi")) or 0 for row in option_chain_rows])
        total_put = sum([_as_float(row.get("put_oi")) or 0 for row in option_chain_rows])
        pcr = (total_put / total_call) if total_call else 0

        market_data["options"] = {
            "chain": option_chain_rows,
            "pcr": pcr,
            "spot": spot_price,
            "expiry": expiry,
        }
    except Exception:
        return market_data

    return market_data
