import datetime as dt
import logging

from dhan_data.client import (
    normalize_exchange_segment,
    sdk_get_market_depth,
    sdk_get_quote,
    sdk_historical_minute_charts,
    sdk_intraday_daily_minute_charts,
)
from dhan_data.option_chain import get_option_chain as fetch_option_chain
from dhan_data.security_map import SECURITY_MAP

_logger = logging.getLogger(__name__)


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _flatten_marketfeed_records(data):
    records = []
    if not isinstance(data, dict):
        return records
    for segment_data in data.values():
        if not isinstance(segment_data, dict):
            continue
        for record in segment_data.values():
            if isinstance(record, dict):
                records.append(record)
    return records


def _extract_quote_records(payload):
    if not payload:
        return []
    data = payload
    if isinstance(payload, dict):
        data = payload.get("data") if "data" in payload else payload
        if isinstance(data, dict) and "data" in data:
            data = data.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        flattened = _flatten_marketfeed_records(data)
        if flattened:
            return flattened
        return [data]
    return []


def extract_ltp(payload):
    records = _extract_quote_records(payload)
    if not records:
        return None
    record = records[0]
    if not isinstance(record, dict):
        return None
    for key in ("ltp", "lastPrice", "last_price", "last_traded_price", "price"):
        if record.get(key) is not None:
            return record.get(key)
    ohlc = record.get("ohlc") if isinstance(record.get("ohlc"), dict) else {}
    return ohlc.get("close")


def _parse_ohlc_series(data):
    if not isinstance(data, dict):
        return []
    payload = data.get("data") if "data" in data else data
    if isinstance(payload, dict) and "candles" in payload and isinstance(payload["candles"], dict):
        payload = payload["candles"]
    if not isinstance(payload, dict):
        return []
    opens = payload.get("open") if payload.get("open") is not None else payload.get("o")
    highs = payload.get("high") if payload.get("high") is not None else payload.get("h")
    lows = payload.get("low") if payload.get("low") is not None else payload.get("l")
    closes = payload.get("close") if payload.get("close") is not None else payload.get("c")
    volumes = payload.get("volume") if payload.get("volume") is not None else payload.get("v")
    times = payload.get("timestamp") if payload.get("timestamp") is not None else payload.get("t")
    if times is None:
        times = payload.get("time")
    opens = opens or []
    highs = highs or []
    lows = lows or []
    closes = closes or []
    volumes = volumes or []
    times = times or []
    length = min(len(opens), len(highs), len(lows), len(closes))
    if length == 0:
        return []
    rows = []
    for idx in range(length):
        rows.append({
            "time": times[idx] if idx < len(times) else None,
            "open": opens[idx],
            "high": highs[idx],
            "low": lows[idx],
            "close": closes[idx],
            "volume": volumes[idx] if idx < len(volumes) else None
        })
    return rows


def get_ltp(security_id, segment):
    segment = normalize_exchange_segment(segment)
    data, err = sdk_get_quote(security_id, segment)
    if err:
        return {"error": err}
    return data


def get_intraday(security_id, segment, extra_params=None):
    segment = normalize_exchange_segment(segment)
    extra_params = extra_params or {}
    instrument = extra_params.get("instrument") or ("INDEX" if segment == "NSE_INDEX" else "EQUITY")
    today = dt.date.today()
    from_date = extra_params.get("fromDate") or dt.datetime.combine(today, dt.time(9, 15)).strftime("%Y-%m-%d %H:%M:%S")
    to_date = extra_params.get("toDate") or dt.datetime.combine(today, dt.time(15, 30)).strftime("%Y-%m-%d %H:%M:%S")
    time_frame = extra_params.get("time_frame") or extra_params.get("interval") or 5
    data, err = sdk_intraday_daily_minute_charts(
        security_id,
        segment,
        instrument,
        from_date,
        to_date,
        time_frame=time_frame,
    )
    if err:
        return {"error": err}
    return {"data": _parse_ohlc_series(data)}


def get_historical(security_id, segment, extra_params=None):
    segment = normalize_exchange_segment(segment)
    extra_params = extra_params or {}
    instrument = extra_params.get("instrument") or ("INDEX" if segment == "NSE_INDEX" else "EQUITY")
    end = extra_params.get("toDate")
    start = extra_params.get("fromDate")
    if not end or not start:
        today = dt.date.today()
        end = end or today.strftime("%Y-%m-%d")
        start = start or (today - dt.timedelta(days=30)).strftime("%Y-%m-%d")
    time_frame = extra_params.get("time_frame") or extra_params.get("interval") or 5
    data, err = sdk_historical_minute_charts(
        security_id,
        segment,
        instrument,
        start,
        end,
        time_frame=time_frame,
    )
    if err:
        return {"error": err}
    return {"data": _parse_ohlc_series(data)}


def get_depth(security_id, segment):
    segment = normalize_exchange_segment(segment)
    data, err = sdk_get_market_depth(security_id, segment)
    if err:
        return {"error": err}
    return data


def _flatten_option_chain(data):
    if not isinstance(data, dict):
        return []
    payload = data.get("data") if "data" in data else data
    if not isinstance(payload, dict):
        return []
    chain = payload.get("oc") or payload.get("records") or payload.get("chain")
    if chain is None:
        return []
    rows = []
    if isinstance(chain, dict):
        for strike, row in chain.items():
            ce = row.get("ce") or row.get("CE") or {}
            pe = row.get("pe") or row.get("PE") or {}
            strike_value = _to_float(strike)
            if ce:
                ce_ltp = ce.get("last_price") or ce.get("ltp")
                rows.append({"strike": strike_value, "type": "CE", "ltp": ce_ltp})
            if pe:
                pe_ltp = pe.get("last_price") or pe.get("ltp")
                rows.append({"strike": strike_value, "type": "PE", "ltp": pe_ltp})
    elif isinstance(chain, list):
        for row in chain:
            strike = _to_float(row.get("strike") or row.get("strike_price") or row.get("strikePrice"))
            opt_type = row.get("option_type") or row.get("optionType") or row.get("type")
            rows.append({"strike": strike, "type": opt_type, "ltp": row.get("ltp")})
    return rows


def get_option_chain(security_id, exchange_segment="NFO"):
    normalized = normalize_exchange_segment(exchange_segment)
    if normalized in ("NSE_INDEX", "NSE_EQ"):
        underlying_segment = normalized
    elif normalized == "NFO":
        index_ids = {
            value for value in (
                SECURITY_MAP.get("NIFTY"),
                SECURITY_MAP.get("BANKNIFTY"),
                SECURITY_MAP.get("FINNIFTY"),
            )
            if value is not None
        }
        try:
            underlying_segment = "NSE_INDEX" if int(security_id) in index_ids else "NSE_EQ"
        except (TypeError, ValueError):
            underlying_segment = "NSE_INDEX"
    else:
        underlying_segment = "NSE_INDEX"
    chain_data, err = fetch_option_chain(security_id, segment=underlying_segment)
    if err:
        return {"error": err}
    rows = _flatten_option_chain(chain_data)
    if not rows:
        _logger.warning("Option chain empty for %s", security_id)
    return rows
