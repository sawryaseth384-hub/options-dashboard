import logging

from dhan_data.client import normalize_exchange_segment, sdk_get_quote, sdk_option_contracts

_logger = logging.getLogger(__name__)


def _normalize_contracts(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "contracts", "result", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def _first_present(data, keys):
    if not isinstance(data, dict):
        return None
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return None


def _extract_expiry(contract):
    return _first_present(contract, ["expiry_date", "expiryDate", "expiry", "Expiry"])


def _extract_strike(contract):
    return _first_present(contract, ["strike_price", "strikePrice", "strike"])


def _extract_option_type(contract):
    opt_type = _first_present(contract, ["option_type", "optionType", "type"])
    if not opt_type:
        return None
    opt_type = str(opt_type).upper()
    if opt_type in {"CE", "CALL"}:
        return "CE"
    if opt_type in {"PE", "PUT"}:
        return "PE"
    return opt_type


def _extract_security_id(contract):
    return _first_present(contract, ["security_id", "securityId", "sid", "scripId"])


def _extract_quote_record(payload):
    if not payload:
        return None
    data = payload
    if isinstance(payload, dict):
        data = payload.get("data") if "data" in payload else payload
        if isinstance(data, dict) and "data" in data:
            data = data.get("data")
    if isinstance(data, list):
        return data[0] if data else None
    if isinstance(data, dict):
        return data
    return None


def _build_leg(quote_record):
    if not isinstance(quote_record, dict):
        return {
            "ltp": None,
            "oi": None,
            "volume": None,
            "iv": None,
            "price_change": None,
            "oi_change": None,
            "last_price": None,
        }
    return {
        "ltp": _first_present(quote_record, ["ltp", "lastPrice", "last_price", "price"]),
        "last_price": _first_present(quote_record, ["ltp", "lastPrice", "last_price", "price"]),
        "oi": _first_present(quote_record, ["oi", "openInterest", "open_interest"]),
        "volume": _first_present(quote_record, ["volume", "tradedVolume", "volumeTraded"]),
        "iv": _first_present(quote_record, ["iv", "impliedVolatility", "implied_volatility"]),
        "price_change": _first_present(quote_record, ["change", "priceChange", "chg"]),
        "oi_change": _first_present(quote_record, ["oiChange", "changeinOpenInterest", "oi_change"]),
    }


def get_option_contracts(security_id, exchange_segment="NFO"):
    exchange_segment = normalize_exchange_segment(exchange_segment) or "NFO"
    data, err = sdk_option_contracts(security_id, exchange_segment)
    if err:
        return [], err
    contracts = _normalize_contracts(data)
    if not contracts:
        return [], "No contracts found"
    return contracts, None


def get_expiry_list(security_id, segment="NSE_INDEX"):
    contracts, err = get_option_contracts(security_id, "NFO")
    if err:
        return [], err
    expiries = sorted({expiry for expiry in (_extract_expiry(c) for c in contracts) if expiry})
    if not expiries:
        return [], "No expiry found"
    return expiries, None


def get_option_chain(security_id, expiry=None, segment=None, exchange_segment=None):
    underlying_segment = normalize_exchange_segment(exchange_segment or segment or "NSE_INDEX") or "NSE_INDEX"
    contracts, err = get_option_contracts(security_id, "NFO")
    if err:
        return None, err
    expiries = sorted({exp for exp in (_extract_expiry(c) for c in contracts) if exp})
    if not expiries:
        return None, "No expiry found"
    selected_expiry = expiry or expiries[0]
    filtered = [c for c in contracts if _extract_expiry(c) == selected_expiry]
    if not filtered:
        return None, f"No contracts found for expiry {selected_expiry}"

    oc = {}
    for contract in filtered:
        strike = _extract_strike(contract)
        opt_type = _extract_option_type(contract)
        sec_id = _extract_security_id(contract)
        if strike is None or opt_type is None or sec_id is None:
            continue
        quote, quote_err = sdk_get_quote(sec_id, "NFO")
        if quote_err:
            _logger.warning("Quote error for %s: %s", sec_id, quote_err)
        record = _extract_quote_record(quote)
        leg = _build_leg(record)
        strike_key = str(strike)
        oc.setdefault(strike_key, {"ce": {}, "pe": {}})
        if opt_type == "CE":
            oc[strike_key]["ce"] = leg
        elif opt_type == "PE":
            oc[strike_key]["pe"] = leg

    spot = None
    spot_payload, spot_err = sdk_get_quote(security_id, underlying_segment)
    if spot_err:
        _logger.warning("Spot quote error for %s: %s", security_id, spot_err)
    else:
        spot_record = _extract_quote_record(spot_payload)
        if isinstance(spot_record, dict):
            spot = _first_present(spot_record, ["ltp", "lastPrice", "last_price", "price"])

    return {
        "status": "success",
        "data": {
            "oc": oc,
            "last_price": spot,
            "expiry": selected_expiry,
        },
        "expiries": expiries,
        "selected_expiry": selected_expiry,
    }, None
