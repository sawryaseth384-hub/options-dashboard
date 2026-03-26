import os

import requests

BASE_URL = "https://api.dhan.co/v2"


def _get_token():
    token = os.getenv("DHAN_ACCESS_TOKEN")
    if token:
        return token.strip()
    try:
        import streamlit as st

        secret_token = st.secrets.get("DHAN_ACCESS_TOKEN")
        if secret_token:
            return str(secret_token).strip()
    except Exception:
        return None
    return None


def get_headers():
    token = _get_token()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["access-token"] = token
    return headers


def safe_request(endpoint, method="GET", params=None, payload=None):
    url = f"{BASE_URL}{endpoint}"
    headers = get_headers()
    if not headers.get("access-token"):
        return {"error": "Missing DHAN_ACCESS_TOKEN"}

    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            params=params,
            json=payload,
            timeout=10,
        )

        if response.status_code == 401:
            return {"error": "Unauthorized - Check token"}
        if response.status_code == 404:
            return {"error": f"Endpoint not found: {endpoint}"}
        if response.status_code == 400:
            return {"error": "Bad request - Check parameters"}
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}"}

        return response.json()

    except Exception as exc:
        return {"error": str(exc)}


def extract_ltp(payload):
    if not isinstance(payload, dict):
        return None
    if "last_traded_price" in payload:
        return payload.get("last_traded_price")
    nested = payload.get("data") or payload.get("result")
    if isinstance(nested, dict):
        if "last_traded_price" in nested:
            return nested.get("last_traded_price")
        if "ltp" in nested:
            return nested.get("ltp")
    return None


def get_ltp(security_id, segment):
    return safe_request(
        "/market/quote",
        params={
            "security_id": security_id,
            "exchange_segment": segment,
        },
    )


def get_intraday(security_id, segment, extra_params=None):
    params = {
        "security_id": security_id,
        "exchange_segment": segment,
    }
    if extra_params:
        params.update(extra_params)
    return safe_request("/charts/intraday", params=params)


def get_historical(security_id, segment, extra_params=None):
    params = {
        "security_id": security_id,
        "exchange_segment": segment,
    }
    if extra_params:
        params.update(extra_params)
    return safe_request("/charts/historical", params=params)


def get_depth(security_id, segment):
    return safe_request(
        "/market/depth",
        params={
            "security_id": security_id,
            "exchange_segment": segment,
        },
    )


def _normalize_contracts(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "contracts", "result", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def get_option_chain(security_id):
    contracts = safe_request(
        "/option/contracts",
        params={
            "security_id": security_id,
            "exchange_segment": "NFO",
        },
    )

    if isinstance(contracts, dict) and "error" in contracts:
        return contracts

    contract_list = _normalize_contracts(contracts)
    if not contract_list:
        return {"error": "No contracts found"}

    expiry_values = [
        c.get("expiry_date")
        for c in contract_list
        if c.get("expiry_date") is not None
    ]
    expiries = sorted({expiry for expiry in expiry_values if expiry})

    if not expiries:
        return {"error": "No expiry found"}

    nearest_expiry = expiries[0]
    filtered = [c for c in contract_list if c.get("expiry_date") == nearest_expiry]

    chain = []
    ltp_cache = {}

    for contract in filtered:
        contract_id = contract.get("security_id")
        if contract_id in ltp_cache:
            ltp = ltp_cache[contract_id]
        else:
            quote = get_ltp(contract_id, "NFO")
            ltp = extract_ltp(quote) if isinstance(quote, dict) else None
            if ltp is None:
                ltp = 0
            ltp_cache[contract_id] = ltp

        chain.append(
            {
                "strike": contract.get("strike_price"),
                "type": contract.get("option_type"),
                "ltp": ltp,
            }
        )

    return chain
