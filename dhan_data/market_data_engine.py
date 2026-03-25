import time

from dhan_data.client import DhanApiClient
from dhan_data.instruments import get_stock_df, get_symbol_data, load_instruments


INDEX_SPECS = {
    "nifty": {"symbols": ["NIFTY"], "fallback": (13, "IDX_I")},
    "banknifty": {"symbols": ["BANKNIFTY"], "fallback": (25, "IDX_I")},
    "finnifty": {"symbols": ["FINNIFTY"], "fallback": (27, "IDX_I")},
    "vix": {"symbols": ["INDIAVIX", "VIX"], "fallback": (None, "IDX_I")},
}


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_value(item, keys):
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return None


def _normalize_segment(segment):
    if not segment:
        return "NSE_EQ"
    segment = str(segment).upper()
    if segment in {"IDX_I", "I", "IDX"}:
        return "IDX_I"
    return "NSE_EQ"


def _lookup_security(symbols, fallback):
    for symbol in symbols:
        security_id, segment = get_symbol_data(symbol)
        if security_id:
            return int(security_id), _normalize_segment(segment)

    try:
        instruments = load_instruments()
        if not instruments.empty:
            match = instruments[instruments["SEM_TRADING_SYMBOL"].str.upper().isin([s.upper() for s in symbols])]
            if not match.empty:
                row = match.iloc[0]
                return int(row["SEM_SMST_SECURITY_ID"]), _normalize_segment(row.get("SEGMENT"))
    except (AttributeError, KeyError, TypeError, ValueError):
        pass

    return fallback


def _build_instruments(items):
    return [
        {
            "exchangeSegment": item["segment"],
            "securityId": int(item["security_id"]),
        }
        for item in items
        if item.get("security_id") and item.get("segment")
    ]


def _parse_quotes(raw, instruments):
    data = raw.get("data") if isinstance(raw, dict) else None
    if not isinstance(data, list):
        return {}

    quote_map = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        security_id = _extract_value(item, ["securityId", "security_id", "securityID", "security"])
        if security_id is None:
            continue
        quote_map[int(security_id)] = item

    results = {}
    for instrument in instruments:
        security_id = int(instrument["security_id"])
        symbol = instrument["symbol"]
        quote = quote_map.get(security_id, {})
        ltp = _safe_float(_extract_value(quote, ["lastPrice", "ltp", "LTP", "last_price", "price", "lastTradedPrice"]))
        change = _safe_float(_extract_value(quote, ["netChange", "change", "delta", "changeValue"]))
        change_pct = _safe_float(_extract_value(quote, ["pChange", "changePercent", "change_percentage", "changePct", "percentChange"]))
        prev_close = _safe_float(_extract_value(quote, ["previousClose", "prevClose", "prev_close", "close"]))
        if change_pct is None and change is not None and prev_close:
            change_pct = (change / prev_close) * 100

        results[symbol] = {
            "ltp": ltp,
            "change": change,
            "change_pct": change_pct,
        }
    return results


def _fetch_market_quotes(client, instruments):
    if not instruments:
        return {}
    payload = {"instruments": _build_instruments(instruments)}
    data, err = client.post("marketquote", payload)
    if err or not data:
        return {}
    return _parse_quotes(data, instruments)


def _extract_expiry_list(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("data") or data.get("expiry") or []
    return []


def _normalize_chain(chain):
    normalized = []
    if isinstance(chain, dict):
        items = chain.items()
    elif isinstance(chain, list):
        items = [(row.get("strike") or row.get("Strike") or row.get("strikePrice"), row) for row in chain if isinstance(row, dict)]
    else:
        return normalized

    for strike, row in items:
        if not isinstance(row, dict):
            continue
        ce = row.get("ce") or row.get("CE") or row.get("call") or {}
        pe = row.get("pe") or row.get("PE") or row.get("put") or {}
        normalized.append({
            "strike": _safe_float(strike),
            "call_oi": _safe_float(_extract_value(ce, ["oi", "openInterest"])),
            "put_oi": _safe_float(_extract_value(pe, ["oi", "openInterest"])),
            "call_ltp": _safe_float(_extract_value(ce, ["ltp", "last_price", "lastPrice"])),
            "put_ltp": _safe_float(_extract_value(pe, ["ltp", "last_price", "lastPrice"])),
        })
    return normalized


def _fetch_option_chain(client, security_id, segment):
    expiry_data, err = client.post(
        "optionchain/expirylist",
        {"UnderlyingScrip": int(security_id), "UnderlyingSeg": segment},
    )
    if err or not expiry_data:
        return {}, []

    expiries = _extract_expiry_list(expiry_data)
    if not expiries:
        return {}, []

    expiry = expiries[0]
    chain_data, err = client.post(
        "optionchain",
        {"UnderlyingScrip": int(security_id), "UnderlyingSeg": segment, "Expiry": expiry},
    )
    if err or not chain_data:
        return {}, []

    data = chain_data.get("data", {}) if isinstance(chain_data, dict) else {}
    chain = data.get("oc") or data.get("records") or data.get("chain") or {}
    spot = _safe_float(
        _extract_value(
            data,
            ["last_price", "spot", "spotPrice", "underlying_ltp", "ltp"],
        )
    )

    normalized = _normalize_chain(chain)
    return {"spot": spot, "expiry": expiry}, normalized


def build_market_data():
    market_data = {
        "indian": {
            "nifty": {},
            "banknifty": {},
            "finnifty": {},
            "vix": {},
        },
        "stocks": [],
        "options": {
            "chain": [],
            "pcr": 0,
        },
    }

    try:
        client = DhanApiClient()

        index_instruments = []
        for key, spec in INDEX_SPECS.items():
            security_id, segment = _lookup_security(spec["symbols"], spec["fallback"])
            if security_id:
                index_instruments.append({
                    "symbol": key.upper(),
                    "security_id": security_id,
                    "segment": segment,
                })

        index_quotes = _fetch_market_quotes(client, index_instruments)
        for key in market_data["indian"]:
            quote = index_quotes.get(key.upper(), {})
            market_data["indian"][key] = quote

        stock_df = get_stock_df()
        stock_rows = stock_df.head(20) if not stock_df.empty else None
        stock_instruments = []
        if stock_rows is not None:
            for _, row in stock_rows.iterrows():
                security_id = row.get("SEM_SMST_SECURITY_ID")
                symbol = row.get("SEM_TRADING_SYMBOL")
                if security_id and symbol:
                    stock_instruments.append({
                        "symbol": str(symbol).upper(),
                        "security_id": int(security_id),
                        "segment": "NSE_EQ",
                    })

        stock_quotes = _fetch_market_quotes(client, stock_instruments)
        for instrument in stock_instruments:
            symbol = instrument["symbol"]
            quote = stock_quotes.get(symbol, {})
            market_data["stocks"].append({
                "symbol": symbol,
                "ltp": quote.get("ltp"),
                "change_pct": quote.get("change_pct"),
                "change": quote.get("change"),
            })

        if index_instruments:
            option_security = index_instruments[0]
            chain_meta, chain = _fetch_option_chain(client, option_security["security_id"], option_security["segment"])
            market_data["options"]["chain"] = chain
            market_data["options"]["spot"] = chain_meta.get("spot")
            total_call = sum(item.get("call_oi") or 0 for item in chain)
            total_put = sum(item.get("put_oi") or 0 for item in chain)
            if total_call:
                market_data["options"]["pcr"] = total_put / total_call
            else:
                market_data["options"]["pcr"] = None

        return market_data
    except (AttributeError, KeyError, TypeError, ValueError):
        return market_data
