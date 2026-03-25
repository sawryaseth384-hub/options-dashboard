import datetime as dt
import threading
import time

from dhan_data.client import DhanApiClient
from dhan_data.instruments import get_symbol_data, load_instruments

DEFAULT_INDEX_FALLBACKS = {
    "NIFTY": (13, "IDX_I"),
    "BANKNIFTY": (25, "IDX_I"),
    "FINNIFTY": (27, "IDX_I"),
}

DEFAULT_INDEX_SYMBOLS = ["NIFTY", "BANKNIFTY", "FINNIFTY", "VIX"]

STANDARD_FIELDS = ("ltp", "change", "change_pct", "high", "low", "open")

class TTLCache:
    """Simple TTL cache with lazy expiry cleanup and lock-based safety."""
    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()

    def get(self, key):
        """Return cached value if present and not expired."""
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            expires_at, value = item
            if time.time() > expires_at:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key, value, ttl):
        """Cache a value for ttl seconds; non-positive ttl values are ignored."""
        if ttl <= 0:
            return
        with self._lock:
            self._store[key] = (time.time() + ttl, value)

def _instrument_key(security_id, segment):
    return f"{segment}:{security_id}"

def _coalesce(value_map, keys, default=0):
    for key in keys:
        value = _get_nested(value_map, key)
        if value is not None:
            return _normalize_number(value)
    return _normalize_number(default)

def _get_nested(value_map, key):
    if not isinstance(value_map, dict):
        return None
    if "." not in key:
        return value_map.get(key)
    current = value_map
    for part in key.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current

def _normalize_number(value):
    try:
        if value is None:
            return 0
        if isinstance(value, bool):
            return int(value)
        return float(value)
    except (TypeError, ValueError):
        return 0

def _extract_leg(option_leg):
    option_leg = option_leg or {}
    return {
        "oi": _coalesce(option_leg, ["oi", "openInterest", "open_interest", "callOi", "putOi"]),
        "ltp": _coalesce(option_leg, ["last_price", "lastPrice", "ltp"]),
        "iv": _coalesce(option_leg, ["implied_volatility", "impliedVolatility", "iv"]),
        "volume": _coalesce(option_leg, ["volume", "totalTradedVolume", "tradeVolume"]),
        "delta": _coalesce(option_leg, ["greeks.delta", "delta"]),
        "gamma": _coalesce(option_leg, ["greeks.gamma", "gamma"]),
        "theta": _coalesce(option_leg, ["greeks.theta", "theta"]),
        "vega": _coalesce(option_leg, ["greeks.vega", "vega"]),
    }

def _normalize_option_chain(raw_data):
    if not raw_data:
        return [], 0

    data = raw_data.get("data") if isinstance(raw_data, dict) else raw_data
    spot = _coalesce(
        data if isinstance(data, dict) else {},
        ["last_price", "lastPrice", "spotPrice", "underlyingValue", "underlyingPrice"],
        default=0,
    )

    oc = None
    if isinstance(data, dict):
        oc = data.get("oc") or data.get("records") or data.get("data") or data
    elif isinstance(data, list):
        oc = data

    rows = []
    if isinstance(oc, dict):
        for strike_key, row in oc.items():
            strike = _coalesce(row, ["strikePrice", "strike", "strike_price"], default=0)
            if not strike:
                strike = _normalize_number(strike_key)
            ce = row.get("ce") or row.get("CE") or row.get("call") or {}
            pe = row.get("pe") or row.get("PE") or row.get("put") or {}
            if ce or pe:
                rows.append(_build_chain_row(strike, ce, pe))
            else:
                rows.append(_build_flat_chain_row(strike, row))
    elif isinstance(oc, list):
        for row in oc:
            if not isinstance(row, dict):
                continue
            strike = _coalesce(row, ["strikePrice", "strike", "strike_price"], default=0)
            ce = row.get("ce") or row.get("CE") or {}
            pe = row.get("pe") or row.get("PE") or {}
            if ce or pe:
                rows.append(_build_chain_row(strike, ce, pe))
            else:
                rows.append(_build_flat_chain_row(strike, row))

    return rows, spot

def _build_chain_row(strike, ce, pe):
    call = _extract_leg(ce)
    put = _extract_leg(pe)
    return {
        "strike": strike,
        "call_oi": call["oi"],
        "call_ltp": call["ltp"],
        "call_iv": call["iv"],
        "call_volume": call["volume"],
        "call_delta": call["delta"],
        "call_gamma": call["gamma"],
        "call_theta": call["theta"],
        "call_vega": call["vega"],
        "put_oi": put["oi"],
        "put_ltp": put["ltp"],
        "put_iv": put["iv"],
        "put_volume": put["volume"],
        "put_delta": put["delta"],
        "put_gamma": put["gamma"],
        "put_theta": put["theta"],
        "put_vega": put["vega"],
    }

def _build_flat_chain_row(strike, row):
    """Handle flat option chain rows with call/put fields."""
    return {
        "strike": strike,
        "call_oi": _coalesce(row, ["callOi", "call_oi", "ceOi", "CE_OI"]),
        "call_ltp": _coalesce(row, ["callLtp", "call_ltp", "ceLtp", "CE_LTP"]),
        "call_iv": _coalesce(row, ["callIv", "call_iv", "ceIv"]),
        "call_volume": _coalesce(row, ["callVolume", "call_volume", "ceVolume"]),
        "call_delta": _coalesce(row, ["callDelta", "call_delta"]),
        "call_gamma": _coalesce(row, ["callGamma", "call_gamma"]),
        "call_theta": _coalesce(row, ["callTheta", "call_theta"]),
        "call_vega": _coalesce(row, ["callVega", "call_vega"]),
        "put_oi": _coalesce(row, ["putOi", "put_oi", "peOi", "PE_OI"]),
        "put_ltp": _coalesce(row, ["putLtp", "put_ltp", "peLtp", "PE_LTP"]),
        "put_iv": _coalesce(row, ["putIv", "put_iv", "peIv"]),
        "put_volume": _coalesce(row, ["putVolume", "put_volume", "peVolume"]),
        "put_delta": _coalesce(row, ["putDelta", "put_delta"]),
        "put_gamma": _coalesce(row, ["putGamma", "put_gamma"]),
        "put_theta": _coalesce(row, ["putTheta", "put_theta"]),
        "put_vega": _coalesce(row, ["putVega", "put_vega"]),
    }

def _calculate_pcr(rows):
    total_call = sum(row.get("call_oi", 0) for row in rows)
    total_put = sum(row.get("put_oi", 0) for row in rows)
    if not total_call:
        return 0
    return round(total_put / total_call, 4)

def _resolve_chart_segment(segment):
    return "NSE_EQ" if segment == "IDX_I" else segment

def _resolve_instrument_type(segment):
    return "INDEX" if segment == "IDX_I" else "EQUITY"

def _format_date(value, with_time=False):
    if isinstance(value, dt.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S") if with_time else value.strftime("%Y-%m-%d")
    if isinstance(value, dt.date):
        return value.strftime("%Y-%m-%d")
    return str(value)

def _normalize_candles(payload):
    if not payload:
        return []
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []

    timestamps = payload.get("timestamp") or payload.get("time") or []
    open_values = payload.get("open") or []
    high_values = payload.get("high") or []
    low_values = payload.get("low") or []
    close_values = payload.get("close") or []
    volume_values = payload.get("volume") or []
    oi_values = payload.get("oi") or []

    lengths = [
        len(values) for values in [
            timestamps,
            open_values,
            high_values,
            low_values,
            close_values,
            volume_values,
            oi_values,
        ]
        if isinstance(values, list)
    ]
    length = min(lengths) if lengths else 0
    candles = []
    for idx in range(length):
        candles.append({
            "timestamp": timestamps[idx] if idx < len(timestamps) else None,
            "open": open_values[idx] if idx < len(open_values) else None,
            "high": high_values[idx] if idx < len(high_values) else None,
            "low": low_values[idx] if idx < len(low_values) else None,
            "close": close_values[idx] if idx < len(close_values) else None,
            "volume": volume_values[idx] if idx < len(volume_values) else None,
            "oi": oi_values[idx] if idx < len(oi_values) else None,
        })
    return candles

def _extract_market_items(data):
    if not data:
        return []
    if isinstance(data, dict):
        data = data.get("data", data)
    if isinstance(data, dict):
        return list(data.values())
    if isinstance(data, list):
        return data
    return []

def _index_key(symbol):
    symbol_upper = (symbol or "").upper()
    if "BANKNIFTY" in symbol_upper:
        return "banknifty"
    if "FINNIFTY" in symbol_upper:
        return "finnifty"
    if "NIFTY" in symbol_upper:
        return "nifty"
    if "VIX" in symbol_upper:
        return "vix"
    return None

def _normalize_quote_item(quote):
    """Normalize quote payload into the standard price fields."""
    ltp = _coalesce(quote, ["ltp", "lastPrice", "last_price", "close"])
    change = _coalesce(quote, ["netChange", "change", "net_change"])
    change_pct = _coalesce(quote, ["percentChange", "changePercent", "netChangePercent"], default=None)
    if change_pct is None and ltp:
        base = ltp - change
        change_pct = round((change / base) * 100, 4) if base else 0
    return {
        "ltp": ltp,
        "change": change,
        "change_pct": _normalize_number(change_pct),
        "high": _coalesce(quote, ["high", "highPrice", "dayHigh"]),
        "low": _coalesce(quote, ["low", "lowPrice", "dayLow"]),
        "open": _coalesce(quote, ["open", "openPrice", "dayOpen"]),
    }

class MarketDataEngine:
    """Data engine that fetches, normalizes, and caches Dhan market data."""
    def __init__(self, client=None, cache=None):
        self.client = client or DhanApiClient()
        self.cache = cache or TTLCache()
        self._instrument_df = None

    def _get_instrument_df(self):
        if self._instrument_df is None:
            df = load_instruments()
            upper_symbol_col = "SEM_TRADING_SYMBOL_UPPER"
            if not df.empty and upper_symbol_col not in df.columns:
                df = df.copy()
                df[upper_symbol_col] = df["SEM_TRADING_SYMBOL"].str.upper()
            self._instrument_df = df
        return self._instrument_df

    def fetch_expiry_dates(self, security_id, segment="IDX_I", cache_ttl=3600):
        cache_key = ("expiry", segment, int(security_id))
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        payload = {
            "UnderlyingScrip": int(security_id),
            "UnderlyingSeg": segment,
        }
        data, err = self.client.post("/optionchain/expirylist", payload)
        if err:
            return []
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        expiries = data if isinstance(data, list) else []
        if isinstance(expiries, list):
            try:
                expiries = sorted(expiries)
            except TypeError:
                pass
        self.cache.set(cache_key, expiries, cache_ttl)
        return expiries

    def fetch_market_quotes(self, instruments, cache_ttl=1):
        if not instruments:
            return {}
        key_parts = sorted(
            _instrument_key(item.get("security_id"), item.get("segment"))
            for item in instruments
            if item.get("security_id") is not None and item.get("segment")
        )
        cache_key = ("marketquote", tuple(key_parts))
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        payload_instruments = []
        for inst in instruments:
            security_id = inst.get("security_id")
            segment = inst.get("segment")
            if security_id is None or not segment:
                continue
            payload_instruments.append({
                "exchangeSegment": segment,
                "securityId": int(security_id),
            })
        if not payload_instruments:
            return {}

        payload = {"instruments": payload_instruments}

        data, err = self.client.post("/marketfeed/quote", payload)
        if err or not data:
            data, err = self.client.post("/marketquote", payload)
        if err or not data:
            return {}

        quotes = {}
        for item in _extract_market_items(data):
            if not isinstance(item, dict):
                continue
            security_id = item.get("securityId") or item.get("security_id")
            segment = item.get("exchangeSegment") or item.get("segment")
            if security_id is None or not segment:
                continue
            quotes[_instrument_key(security_id, segment)] = item

        self.cache.set(cache_key, quotes, cache_ttl)
        return quotes

    def fetch_market_ltp(self, instruments, cache_ttl=1):
        if not instruments:
            return {}
        key_parts = sorted(
            _instrument_key(item.get("security_id"), item.get("segment"))
            for item in instruments
            if item.get("security_id") is not None and item.get("segment")
        )
        cache_key = ("marketltp", tuple(key_parts))
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        payload_instruments = []
        for inst in instruments:
            security_id = inst.get("security_id")
            segment = inst.get("segment")
            if security_id is None or not segment:
                continue
            payload_instruments.append({
                "exchangeSegment": segment,
                "securityId": int(security_id),
            })
        if not payload_instruments:
            return {}

        payload = {"instruments": payload_instruments}

        data, err = self.client.post("/marketfeed/ltp", payload)
        if err or not data:
            return {}

        ltps = {}
        for item in _extract_market_items(data):
            if not isinstance(item, dict):
                continue
            security_id = item.get("securityId") or item.get("security_id")
            segment = item.get("exchangeSegment") or item.get("segment")
            if security_id is None or not segment:
                continue
            ltps[_instrument_key(security_id, segment)] = item

        self.cache.set(cache_key, ltps, cache_ttl)
        return ltps

    def fetch_option_chain(self, security_id, segment="IDX_I", expiry=None, cache_ttl=5):
        if expiry is None:
            expiries = self.fetch_expiry_dates(security_id, segment=segment)
            if expiries:
                try:
                    expiry = min(expiries)
                except TypeError:
                    expiry = expiries[0]
            else:
                expiry = None

        if not expiry:
            return {"chain": [], "pcr": 0, "spot_price": 0, "expiry": None}

        cache_key = ("optionchain", int(security_id), segment, expiry)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        payload = {
            "UnderlyingScrip": int(security_id),
            "UnderlyingSeg": segment,
            "expiryDate": expiry,
        }

        data, err = self.client.post("/optionchain", payload)
        if err or not data:
            return {"chain": [], "pcr": 0, "spot_price": 0, "expiry": expiry}

        if isinstance(data, dict) and data.get("status") not in (None, "success"):
            return {"chain": [], "pcr": 0, "spot_price": 0, "expiry": expiry}

        chain_rows, spot = _normalize_option_chain(data)
        result = {
            "chain": chain_rows,
            "pcr": _calculate_pcr(chain_rows),
            "spot_price": spot,
            "expiry": expiry,
        }
        self.cache.set(cache_key, result, cache_ttl)
        return result

    def fetch_intraday(self, security_id, segment, interval="1", from_date=None, to_date=None, cache_ttl=30):
        if from_date is None:
            from_date = dt.date.today()
        if to_date is None:
            to_date = dt.date.today()

        from_date = _format_date(from_date)
        to_date = _format_date(to_date)

        cache_key = ("intraday", int(security_id), segment, interval, from_date, to_date)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        payload = {
            "securityId": str(security_id),
            "exchangeSegment": _resolve_chart_segment(segment),
            "instrument": _resolve_instrument_type(segment),
            "interval": str(interval),
            "oi": False,
            "fromDate": from_date,
            "toDate": to_date,
        }

        data, err = self.client.post("/charts/intraday", payload)
        candles = _normalize_candles(data) if not err else []
        self.cache.set(cache_key, candles, cache_ttl)
        return candles

    def fetch_historical(self, security_id, segment, from_date=None, to_date=None, cache_ttl=300):
        if to_date is None:
            to_date = dt.date.today()
        if from_date is None:
            from_date = to_date - dt.timedelta(days=30)

        from_date = _format_date(from_date)
        to_date = _format_date(to_date)

        cache_key = ("historical", int(security_id), segment, from_date, to_date)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        payload = {
            "securityId": str(security_id),
            "exchangeSegment": segment,
            "instrument": _resolve_instrument_type(segment),
            "expiryCode": 0,
            "oi": False,
            "fromDate": from_date,
            "toDate": to_date,
        }

        data, err = self.client.post("/charts/historical", payload)
        candles = _normalize_candles(data) if not err else []
        self.cache.set(cache_key, candles, cache_ttl)
        return candles

    # Public, modular helpers expected by the dashboard.
    def get_indices(self, symbols=None):
        return self.fetch_indices(symbols)

    def get_stocks(self, symbols):
        return self.fetch_stocks(symbols)

    def get_option_chain(self, symbol=None, security_id=None, segment="IDX_I", expiry=None):
        if security_id is None and symbol:
            resolved = self.resolve_symbol(symbol, fallback_segment=segment)
            if resolved:
                security_id = resolved["security_id"]
                segment = resolved["segment"]
        if not security_id:
            return {"chain": [], "pcr": 0, "spot_price": 0, "expiry": expiry}
        return self.fetch_option_chain(security_id, segment=segment, expiry=expiry)

    def get_intraday(self, security_id, segment, interval="1", from_date=None, to_date=None):
        return self.fetch_intraday(
            security_id,
            segment,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
        )

    def resolve_symbol(self, symbol, fallback_segment="NSE_EQ"):
        security_id, segment = get_symbol_data(symbol)
        if security_id:
            return {"symbol": symbol.upper(), "security_id": security_id, "segment": segment}

        fallback = DEFAULT_INDEX_FALLBACKS.get(symbol.upper())
        if fallback:
            return {"symbol": symbol.upper(), "security_id": fallback[0], "segment": fallback[1]}

        df = self._get_instrument_df()
        if df.empty:
            return None

        symbol_upper = symbol.upper()
        upper_symbol_col = "SEM_TRADING_SYMBOL_UPPER"
        symbol_matches = df[df[upper_symbol_col] == symbol_upper]
        if symbol_matches.empty and symbol_upper == "VIX":
            symbol_matches = df[df[upper_symbol_col].str.contains("VIX", na=False)]
        if symbol_matches.empty:
            return None

        if len(symbol_matches) > 1:
            preferred_segments = [fallback_segment, "IDX_I", "I", "NSE_EQ"]
            for seg in preferred_segments:
                candidate = symbol_matches[symbol_matches["SEGMENT"] == seg]
                if not candidate.empty:
                    symbol_matches = candidate
                    break

        row = symbol_matches.iloc[0]
        segment = row.get("SEGMENT") or fallback_segment
        return {
            "symbol": symbol_upper,
            "security_id": int(row["SEM_SMST_SECURITY_ID"]),
            "segment": "IDX_I" if segment in ("I", "IDX_I") else segment,
        }

    def fetch_indices(self, symbols=None):
        symbols = symbols or DEFAULT_INDEX_SYMBOLS
        instruments = []
        for symbol in symbols:
            resolved = self.resolve_symbol(symbol, fallback_segment="IDX_I")
            if resolved:
                instruments.append(resolved)
        # Use quote endpoint for OHLC data and LTP endpoint for live prices.
        quotes = self.fetch_market_quotes(instruments)
        ltps = self.fetch_market_ltp(instruments)
        return self._merge_quotes(instruments, quotes, ltps)

    def fetch_stocks(self, symbols):
        instruments = []
        for symbol in symbols or []:
            resolved = self.resolve_symbol(symbol, fallback_segment="NSE_EQ")
            if resolved:
                instruments.append(resolved)
        quotes = self.fetch_market_quotes(instruments)
        ltps = self.fetch_market_ltp(instruments)
        return self._merge_quotes(instruments, quotes, ltps)

    def _merge_quotes(self, instruments, quotes, ltps=None):
        merged = []
        ltps = ltps or {}
        for inst in instruments:
            key = _instrument_key(inst["security_id"], inst["segment"])
            quote = quotes.get(key, {}).copy()
            ltp_quote = ltps.get(key, {})
            if ltp_quote:
                quote.setdefault("ltp", ltp_quote.get("ltp") or ltp_quote.get("lastPrice"))
            normalized = _normalize_quote_item(quote)
            merged.append({
                "symbol": inst["symbol"],
                "security_id": inst["security_id"],
                "segment": inst["segment"],
                **normalized,
                "quote": quote,
            })
        return merged

    def build_market_data(
        self,
        index_symbols=None,
        stock_symbols=None,
        option_chain_symbol=None,
        option_chain_security_id=None,
        option_chain_segment="IDX_I",
        option_chain_expiry=None,
        include_intraday=False,
        include_historical=False,
        intraday_interval="1",
        intraday_symbols=None,
        historical_symbols=None,
    ):
        market_data = {
            "indian": {
                "nifty": {},
                "banknifty": {},
                "finnifty": {},
                "vix": {},
            },
            "global": {},
            "commodity": {},
            "currency": {},
            "stocks": [],
            "options": {"chain": [], "pcr": 0},
        }

        indices = self.fetch_indices(index_symbols)
        stocks = self.fetch_stocks(stock_symbols or [])

        for index_item in indices:
            key = _index_key(index_item.get("symbol"))
            if not key:
                continue
            market_data["indian"][key] = {
                field: index_item.get(field, 0) for field in STANDARD_FIELDS
            }
        market_data["stocks"] = stocks

        if option_chain_symbol or option_chain_security_id:
            security_id = option_chain_security_id
            segment = option_chain_segment
            underlying_symbol = option_chain_symbol

            if security_id is None and option_chain_symbol:
                resolved = self.resolve_symbol(option_chain_symbol, fallback_segment=option_chain_segment)
                if resolved:
                    security_id = resolved["security_id"]
                    segment = resolved["segment"]
                    underlying_symbol = resolved["symbol"]

            if security_id:
                option_data = self.fetch_option_chain(
                    security_id,
                    segment=segment,
                    expiry=option_chain_expiry,
                )
                option_data["underlying"] = underlying_symbol
                market_data["options"] = option_data

        if include_intraday:
            intraday_targets = intraday_symbols or []
            self._attach_candles(intraday_targets, indices + stocks, "intraday", intraday_interval)

        if include_historical:
            historical_targets = historical_symbols or []
            self._attach_candles(historical_targets, indices + stocks, "historical", None)

        return market_data

    def _attach_candles(self, targets, instruments, candle_type, interval):
        target_set = {symbol.upper() for symbol in targets} if targets else None
        for inst in instruments:
            if target_set and inst["symbol"].upper() not in target_set:
                continue
            if candle_type == "intraday":
                inst["intraday"] = self.fetch_intraday(
                    inst["security_id"],
                    inst["segment"],
                    interval=interval or "1",
                )
            elif candle_type == "historical":
                inst["historical"] = self.fetch_historical(
                    inst["security_id"],
                    inst["segment"],
                )
            else:
                raise ValueError(
                    f"Unsupported candle_type: {candle_type!r}. Expected 'intraday' or 'historical'."
                )

_DEFAULT_ENGINE = MarketDataEngine()

def get_indices(symbols=None):
    """Module-level helper for index quotes."""
    return _DEFAULT_ENGINE.get_indices(symbols)

def get_stocks(symbols):
    """Module-level helper for stock quotes."""
    return _DEFAULT_ENGINE.get_stocks(symbols)

def get_option_chain(symbol=None, security_id=None, segment="IDX_I", expiry=None):
    """Module-level helper for option chain + PCR."""
    return _DEFAULT_ENGINE.get_option_chain(
        symbol=symbol,
        security_id=security_id,
        segment=segment,
        expiry=expiry,
    )

def get_intraday(security_id, segment, interval="1", from_date=None, to_date=None):
    """Module-level helper for intraday candles."""
    return _DEFAULT_ENGINE.get_intraday(
        security_id,
        segment,
        interval=interval,
        from_date=from_date,
        to_date=to_date,
    )

def build_market_data(**kwargs):
    """Module-level helper to assemble the full market_data payload."""
    return _DEFAULT_ENGINE.build_market_data(**kwargs)
