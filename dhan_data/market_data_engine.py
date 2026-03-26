import datetime as dt
import logging
import streamlit as st

from dhan_data.client import BASE_URL, DhanApiClient, safe_post
from dhan_data.expiry import DEFAULT_EXPIRY_FALLBACK, get_expiry_list
from dhan_data.instruments import get_symbol_data, load_instruments
from dhan_data.security_map import SECURITY_MAP


DEFAULT_INDEXES = {
    "NIFTY": {"security_id": SECURITY_MAP["NIFTY"], "segment": "IDX_I"},
    "BANKNIFTY": {"security_id": SECURITY_MAP["BANKNIFTY"], "segment": "IDX_I"},
    "FINNIFTY": {"security_id": SECURITY_MAP["FINNIFTY"], "segment": "IDX_I"},
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
GLOBAL_PLACEHOLDERS = []
CURRENCY_PLACEHOLDERS = []
INDEX_FALLBACKS = {
    symbol: (data["security_id"], data["segment"])
    for symbol, data in DEFAULT_INDEXES.items()
}
STOCK_FALLBACKS = {
    symbol: (sec_id, "NSE_EQ")
    for symbol, sec_id in SECURITY_MAP.items()
    if symbol not in DEFAULT_INDEXES
}

SEGMENT_ALIASES = {
    "D": "NSE_EQ",
    "EQ": "NSE_EQ",
    "NSE_EQ": "NSE_EQ",
    "I": "IDX_I",
    "IDX_I": "IDX_I"
}

_logger = logging.getLogger(__name__)


def _as_float(value):
    try:
        return float(value)
    except Exception:
        return None


def _to_int(value):
    try:
        return int(float(value))
    except Exception:
        return None


def _first_present(data, keys, default=None):
    if not isinstance(data, dict):
        return default
    for key in keys:
        if key in data and data.get(key) is not None:
            return data.get(key)
    return default


def _normalize_symbol(symbol):
    return str(symbol or "").strip().upper()


def _normalize_segment(segment, symbol=None):
    if not segment:
        if symbol in DEFAULT_INDEXES:
            return "IDX_I"
        if symbol in SECURITY_MAP:
            return "NSE_EQ"
        return None
    seg = str(segment).upper()
    if seg in SEGMENT_ALIASES:
        return SEGMENT_ALIASES[seg]
    return seg


def _find_symbol_in_master(symbol_aliases):
    aliases = {_normalize_symbol(sym) for sym in symbol_aliases if sym}
    if not aliases:
        return None, None
    df = load_instruments()
    if df.empty:
        return None, None
    df = df.copy()
    symbol_col = next((c for c in df.columns if "TRADING_SYMBOL" in c.upper()), None)
    id_col = next((c for c in df.columns if "SECURITY_ID" in c.upper()), None)
    seg_col = next((c for c in df.columns if "SEGMENT" in c.upper()), None)
    if not symbol_col or not id_col or not seg_col:
        return None, None
    df["__SYM__"] = df[symbol_col].astype(str).str.upper()
    match = df[df["__SYM__"].isin(aliases)]
    if match.empty:
        return None, None
    row = match.iloc[0]
    return _to_int(row.get(id_col)), row.get(seg_col)


def _resolve_symbol(symbol, fallbacks, aliases=None):
    symbol = _normalize_symbol(symbol)
    sec_id, segment = get_symbol_data(symbol)
    segment = _normalize_segment(segment, symbol)
    if sec_id and segment:
        return sec_id, segment
    if aliases:
        sec_id, segment = _find_symbol_in_master([symbol] + list(aliases))
        segment = _normalize_segment(segment, symbol)
        if sec_id and segment:
            return sec_id, segment
    mapped = SECURITY_MAP.get(symbol)
    if mapped:
        sec_id = _to_int(mapped)
        segment = "IDX_I" if symbol in DEFAULT_INDEXES else "NSE_EQ"
        if sec_id and segment:
            return sec_id, segment
    fallback = fallbacks.get(symbol)
    return fallback if fallback else (None, None)


def _build_placeholder_section(symbols):
    return {symbol: {"symbol": symbol} for symbol in symbols}


def _empty_market_data(errors=None):
    return {
        "indian": {},
        "global": _build_placeholder_section(GLOBAL_PLACEHOLDERS),
        "currency": _build_placeholder_section(CURRENCY_PLACEHOLDERS),
        "stocks": [],
        "options": {
            "chain": [],
            "pcr": 0,
            "atm": None,
            "oi_analysis": {},
            "by_symbol": {},
            "selected_symbol": None,
            "selected_expiry": None
        },
        "intraday": [],
        "historical": [],
        "volume_spike": {"spike": False, "threshold": None, "latest": None},
        "depth": {"symbol": None, "data": {}},
        "_meta": {
            "errors": errors or [],
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat()
        }
    }


@st.cache_data(ttl=5)
def _fetch_ltp(instrument_key):
    try:
        instruments = [
            {"exchangeSegment": seg, "securityId": sec_id}
            for seg, sec_id in instrument_key
        ]
        payload = {"instruments": instruments}
        data, err = safe_post(f"{BASE_URL}/marketfeed/ltp", payload, timeout=5)
    except Exception as exc:
        return [], str(exc)
    if err or not data:
        return [], err
    return _extract_ltp_records(data), None


def _extract_ltp_records(payload):
    if not payload:
        return []
    data = payload.get("data") if isinstance(payload, dict) else payload
    if isinstance(data, dict) and "data" in data:
        data = data.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [v for v in data.values() if isinstance(v, dict)]
    return []


def _map_ltp_record(record):
    ohlc = record.get("ohlc") if isinstance(record, dict) else {}
    return {
        "ltp": _first_present(record, ["ltp", "lastPrice", "last_price", "price"]),
        "change": _first_present(record, ["change", "priceChange", "ch"]),
        "change_pct": _first_present(record, ["changePercent", "change_percentage", "pctChange", "changePercent"]),
        "open": _first_present(record, ["open", "o"], _first_present(ohlc, ["open", "o"])),
        "high": _first_present(record, ["high", "h"], _first_present(ohlc, ["high", "h"])),
        "low": _first_present(record, ["low", "l"], _first_present(ohlc, ["low", "l"])),
        "volume": _first_present(record, ["volume", "vol"], _first_present(ohlc, ["volume", "vol"])),
        "security_id": _first_present(record, ["securityId", "security_id"])
    }


@st.cache_data(ttl=3600)
def _fetch_expiry_list(security_id, segment):
    try:
        payload = {"UnderlyingScrip": int(security_id), "UnderlyingSeg": segment}
        data, err = safe_post(f"{BASE_URL}/optionchain/expirylist", payload, timeout=10)
    except Exception as exc:
        _logger.warning("Expiry list fetch failed: %s", exc)
        return []
    if err or not data:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("data") or []
    return []


@st.cache_data(ttl=30)
def _fetch_option_chain(security_id, segment, expiry):
    try:
        payload = {
            "UnderlyingScrip": int(security_id),
            "UnderlyingSeg": segment,
            "expiryDate": expiry
        }
        data, err = safe_post(f"{BASE_URL}/optionchain", payload, timeout=10)
        return data, err
    except Exception as exc:
        return {}, str(exc)


def _normalize_option_leg(leg):
    if not isinstance(leg, dict):
        return {
            "ltp": None,
            "oi": None,
            "volume": None,
            "iv": None,
            "price_change": None,
            "oi_change": None
        }
    return {
        "ltp": _to_float(_first_present(leg, ["ltp", "lastPrice", "last_price", "price"])),
        "oi": _to_float(_first_present(leg, ["oi", "openInterest", "open_interest"])),
        "volume": _to_float(_first_present(leg, ["volume", "tradedVolume", "volumeTraded"])),
        "iv": _to_float(_first_present(leg, ["iv", "impliedVolatility", "implied_volatility"])),
        "price_change": _to_float(_first_present(leg, ["change", "priceChange", "chg"])),
        "oi_change": _to_float(_first_present(leg, ["oiChange", "changeinOpenInterest", "oi_change"]))
    }


def _parse_option_chain(data):
    if not isinstance(data, dict):
        return None, None, None
    payload = data.get("data") if "data" in data else data
    if not payload:
        return None, None, None
    spot = _first_present(payload, ["spot", "last_price", "underlyingValue", "underlying_ltp", "ltp"])
    chain = payload.get("oc") or payload.get("records") or payload.get("chain")
    if chain is None:
        return None, spot, payload
    rows = []
    if isinstance(chain, dict):
        for strike, row in chain.items():
            ce = _normalize_option_leg(row.get("CE") or row.get("ce") or {})
            pe = _normalize_option_leg(row.get("PE") or row.get("pe") or {})
            rows.append({
                "strike": _to_float(strike),
                "ce": ce,
                "pe": pe
            })
    elif isinstance(chain, list):
        for row in chain:
            strike = _first_present(row, ["strikePrice", "strike", "strike_price"])
            ce = _normalize_option_leg(row.get("CE") or row.get("ce") or row.get("call") or {})
            pe = _normalize_option_leg(row.get("PE") or row.get("pe") or row.get("put") or {})
            rows.append({
                "strike": _to_float(strike),
                "ce": ce,
                "pe": pe
            })
    return rows, spot, payload


def _calculate_pcr(chain_rows):
    total_call = 0
    total_put = 0
    for row in chain_rows or []:
        total_call += row.get("ce", {}).get("oi") or 0
        total_put += row.get("pe", {}).get("oi") or 0
    if total_call:
        return total_put / total_call
    return None


def _calculate_atm(chain_rows, spot):
    if spot is None:
        return None
    strikes = [row.get("strike") for row in chain_rows if row.get("strike") is not None]
    if not strikes:
        return None
    return min(strikes, key=lambda s: abs(s - spot))


def _filter_strikes(chain_rows, atm_strike, window=10):
    if not chain_rows or atm_strike is None:
        return chain_rows
    strikes = sorted({row.get("strike") for row in chain_rows if row.get("strike") is not None})
    if not strikes:
        return chain_rows
    try:
        atm_index = strikes.index(atm_strike)
    except ValueError:
        atm_index = min(range(len(strikes)), key=lambda idx: abs(strikes[idx] - atm_strike))
    lower = max(0, atm_index - window)
    upper = min(len(strikes), atm_index + window + 1)
    allowed = set(strikes[lower:upper])
    return [row for row in chain_rows if row.get("strike") in allowed]


def _classify_oi(price_change, oi_change):
    if price_change is None or oi_change is None:
        return "Unknown"
    if price_change > 0 and oi_change > 0:
        return "Long Build-up"
    if price_change < 0 and oi_change > 0:
        return "Short Build-up"
    if price_change > 0 and oi_change < 0:
        return "Short Covering"
    if price_change < 0 and oi_change < 0:
        return "Long Unwinding"
    return "Neutral"


def _oi_analysis(chain_rows):
    summary = {
        "Long Build-up": 0,
        "Short Build-up": 0,
        "Short Covering": 0,
        "Long Unwinding": 0,
        "Neutral": 0,
        "Unknown": 0
    }
    details = []
    for row in chain_rows or []:
        ce_signal = _classify_oi(row.get("ce", {}).get("price_change"), row.get("ce", {}).get("oi_change"))
        pe_signal = _classify_oi(row.get("pe", {}).get("price_change"), row.get("pe", {}).get("oi_change"))
        summary[ce_signal] = summary.get(ce_signal, 0) + 1
        summary[pe_signal] = summary.get(pe_signal, 0) + 1
        details.append({
            "strike": row.get("strike"),
            "ce_signal": ce_signal,
            "pe_signal": pe_signal
        })
    return {"summary": summary, "details": details}


@st.cache_data(ttl=30)
def _fetch_intraday(security_id, segment):
    try:
        instrument = "INDEX" if segment == "IDX_I" else "EQUITY"
        today = dt.date.today()
        from_date = dt.datetime.combine(today, dt.time(9, 15)).strftime("%Y-%m-%d %H:%M:%S")
        to_date = dt.datetime.combine(today, dt.time(15, 30)).strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": segment,
            "instrument": instrument,
            "interval": "5",
            "oi": False,
            "fromDate": from_date,
            "toDate": to_date
        }
        data, err = safe_post(f"{BASE_URL}/charts/intraday", payload, timeout=10)
    except Exception as exc:
        return [], str(exc)
    if err or not data:
        return [], err
    return _parse_ohlc_series(data), None


@st.cache_data(ttl=3600)
def _fetch_historical(security_id, segment):
    try:
        instrument = "INDEX" if segment == "IDX_I" else "EQUITY"
        end = dt.date.today()
        start = end - dt.timedelta(days=30)
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": segment,
            "instrument": instrument,
            "expiryCode": 0,
            "oi": False,
            "fromDate": start.strftime("%Y-%m-%d"),
            "toDate": end.strftime("%Y-%m-%d")
        }
        data, err = safe_post(f"{BASE_URL}/charts/historical", payload, timeout=10)
    except Exception as exc:
        return [], str(exc)
    if err or not data:
        return [], err
    return _parse_ohlc_series(data), None


def _parse_ohlc_series(data):
    if not isinstance(data, dict):
        return []
    if "data" in data and isinstance(data.get("data"), dict):
        data = data.get("data")
    if "candles" in data and isinstance(data.get("candles"), dict):
        data = data.get("candles")
    opens = data.get("open") or data.get("o") or []
    highs = data.get("high") or data.get("h") or []
    lows = data.get("low") or data.get("l") or []
    closes = data.get("close") or data.get("c") or []
    volumes = data.get("volume") or data.get("v") or []
    times = data.get("timestamp") or data.get("t") or data.get("time") or []
    length = min(len(opens), len(highs), len(lows), len(closes))
    if length == 0:
        return []
    rows = []
    for idx in range(length):
        rows.append({
            "time": times[idx] if idx < len(times) else None,
            "open": _to_float(opens[idx]),
            "high": _to_float(highs[idx]),
            "low": _to_float(lows[idx]),
            "close": _to_float(closes[idx]),
            "volume": _to_float(volumes[idx]) if idx < len(volumes) else None
        })
    return rows


def _detect_volume_spike(intraday_rows):
    volumes = [row.get("volume") for row in intraday_rows or [] if row.get("volume") is not None]
    if len(volumes) < 5:
        return {"spike": False, "threshold": None, "latest": None}
    avg = sum(volumes) / len(volumes)
    variance = sum((v - avg) ** 2 for v in volumes) / len(volumes)
    std = variance ** 0.5
    latest = volumes[-1]
    threshold = avg + (2 * std)
    return {
        "spike": latest > threshold,
        "threshold": threshold,
        "latest": latest
    }


@st.cache_data(ttl=10)
def _build_market_data():
    errors = []

    index_symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "VIX"]
    stock_symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]

    index_instruments = []
    index_map = {}
    index_order = []
    for symbol in index_symbols:
        aliases = ["INDIA VIX", "INDIAVIX"] if symbol == "VIX" else None
        sec_id, seg = _resolve_symbol(symbol, INDEX_FALLBACKS, aliases=aliases)
        if sec_id and seg:
            index_instruments.append((seg, sec_id))
            index_map[sec_id] = symbol
            index_order.append(symbol)
        else:
            errors.append(f"Missing securityId for {symbol}")

    stock_instruments = []
    stock_map = {}
    stock_order = []
    for symbol in stock_symbols:
        sec_id, seg = _resolve_symbol(symbol, STOCK_FALLBACKS)
        if sec_id and seg:
            stock_instruments.append((seg, sec_id))
            stock_map[sec_id] = symbol
            stock_order.append(symbol)
        else:
            errors.append(f"Missing securityId for {symbol}")

    indian_section = {}
    if index_instruments:
        try:
            records, err = _fetch_ltp(tuple(index_instruments))
        except Exception as exc:
            records, err = [], str(exc)
        if err:
            errors.append(f"Index LTP error: {err}")
        for idx, record in enumerate(records):
            mapped = _map_ltp_record(record)
            symbol = index_map.get(mapped.get("security_id")) or (index_order[idx] if idx < len(index_order) else None)
            if symbol:
                indian_section[symbol] = {
                    "symbol": symbol,
                    "ltp": mapped.get("ltp"),
                    "change": mapped.get("change"),
                    "change_pct": mapped.get("change_pct"),
                    "open": mapped.get("open"),
                    "high": mapped.get("high"),
                    "low": mapped.get("low")
                }

    stocks = []
    if stock_instruments:
        try:
            records, err = _fetch_ltp(tuple(stock_instruments))
        except Exception as exc:
            records, err = [], str(exc)
        if err:
            errors.append(f"Stock LTP error: {err}")
        for idx, record in enumerate(records):
            mapped = _map_ltp_record(record)
            symbol = stock_map.get(mapped.get("security_id")) or (stock_order[idx] if idx < len(stock_order) else None)
            if symbol:
                stocks.append({
                    "symbol": symbol,
                    "ltp": mapped.get("ltp"),
                    "volume": mapped.get("volume"),
                    "change": mapped.get("change"),
                    "change_pct": mapped.get("change_pct"),
                    "high": mapped.get("high"),
                    "low": mapped.get("low")
                })

    options_by_symbol = {}
    for symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY"]:
        sec_id, segment = _resolve_symbol(symbol, INDEX_FALLBACKS)
        if not sec_id:
            errors.append(f"Option chain missing securityId for {symbol}")
            continue
        segment = segment or "IDX_I"
        try:
            expiries = get_expiry_list(symbol, segment)
        except Exception as exc:
            errors.append(f"{symbol} expiry error: {exc}")
            expiries = [DEFAULT_EXPIRY_FALLBACK]
        if not expiries:
            expiries = [DEFAULT_EXPIRY_FALLBACK]
            errors.append(f"Option expiry missing for {symbol}")
        current_expiry = expiries[0] if expiries else None
        next_expiry = expiries[1] if len(expiries) > 1 else None
        chains = {}
        for expiry in [current_expiry, next_expiry]:
            if not expiry:
                continue
            raw_chain, err = _fetch_option_chain(sec_id, segment, expiry)
            if err:
                errors.append(f"{symbol} option chain error: {err}")
                continue
            chain_rows, spot, payload = _parse_option_chain(raw_chain or {})
            if not chain_rows:
                errors.append(f"{symbol} option chain empty for {expiry}")
                continue
            pcr = _calculate_pcr(chain_rows)
            atm = _calculate_atm(chain_rows, _to_float(spot))
            filtered = _filter_strikes(chain_rows, atm, window=10)
            chains[expiry] = {
                "chain": chain_rows,
                "chain_filtered": filtered,
                "spot": _to_float(spot),
                "pcr": pcr,
                "atm": atm,
                "oi_analysis": _oi_analysis(filtered),
                "payload": payload
            }
        options_by_symbol[symbol] = {
            "expiries": expiries,
            "current_expiry": current_expiry,
            "next_expiry": next_expiry,
            "chains": chains
        }

    default_symbol = "NIFTY" if "NIFTY" in options_by_symbol else next(iter(options_by_symbol), None)
    default_expiry = None
    default_chain = []
    default_pcr = None
    default_atm = None
    default_oi = {}
    if default_symbol:
        symbol_data = options_by_symbol.get(default_symbol, {})
        default_expiry = symbol_data.get("current_expiry")
        chain_data = symbol_data.get("chains", {}).get(default_expiry, {})
        default_chain = chain_data.get("chain_filtered") or chain_data.get("chain") or []
        default_pcr = chain_data.get("pcr")
        default_atm = chain_data.get("atm")
        default_oi = chain_data.get("oi_analysis") or {}
    if default_pcr is None and not default_chain:
        default_pcr = 0
        if default_symbol:
            _logger.info("PCR fallback used for %s", default_symbol)

    intraday_rows = []
    historical_rows = []
    volume_spike = {"spike": False, "threshold": None, "latest": None}
    if default_symbol:
        sec_id, seg = _resolve_symbol(default_symbol, INDEX_FALLBACKS)
        intraday_rows, err = _fetch_intraday(sec_id, seg)
        if err:
            errors.append(f"Intraday error: {err}")
        historical_rows, err = _fetch_historical(sec_id, seg)
        if err:
            errors.append(f"Historical error: {err}")
        volume_spike = _detect_volume_spike(intraday_rows)

    depth_data = {}
    depth_symbol = "RELIANCE"
    sec_id, seg = _resolve_symbol(depth_symbol, STOCK_FALLBACKS)
    if sec_id and seg:
        payload = {"instruments": [{"exchangeSegment": seg, "securityId": sec_id}]}
        try:
            depth_data, err = safe_post(f"{BASE_URL}/marketfeed/quote", payload, timeout=10)
        except Exception as exc:
            depth_data, err = {}, str(exc)
        if err:
            errors.append(f"Depth error: {err}")
            depth_data = {}

    market_data = {
        "indian": indian_section,
        "global": _build_placeholder_section(GLOBAL_PLACEHOLDERS),
        "currency": _build_placeholder_section(CURRENCY_PLACEHOLDERS),
        "stocks": stocks,
        "options": {
            "chain": default_chain,
            "pcr": default_pcr,
            "atm": default_atm,
            "oi_analysis": default_oi,
            "by_symbol": options_by_symbol,
            "selected_symbol": default_symbol,
            "selected_expiry": default_expiry
        },
        "intraday": intraday_rows,
        "historical": historical_rows,
        "volume_spike": volume_spike,
        "depth": {
            "symbol": depth_symbol,
            "data": depth_data
        },
        "_meta": {
            "errors": errors,
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat()
        }
    }
    return market_data


def build_market_data():
    try:
        return _build_market_data()
    except Exception as exc:
        return _empty_market_data([f"Market data error: {exc}"])
