import os
import json
import time
import logging
from datetime import datetime, timezone

import requests
import pandas as pd
from dash import Dash, html, dcc, Input, Output, State, dash_table
from dash.exceptions import PreventUpdate

# ---------------- LOGGING (Gunicorn compatible) ----------------
logger = logging.getLogger("gunicorn.error")
logger.setLevel(logging.INFO)

print("APP IMPORTED")

# ---------------- ENV / CONFIG ----------------
PORT = int(os.environ.get("PORT", 8080))

CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "").strip()

DHAN_HEADERS = {
    "access-token": ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
}

DHAN_LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
DHAN_OPTION_CHAIN_URL = "https://api.dhan.co/v2/optionchain"           # best-effort
DHAN_OPTION_EXPIRIES_URL = "https://api.dhan.co/v2/optionchain/expiry"  # best-effort

REQUEST_TIMEOUT_SECS = 8

SEGMENTS = ["INDEX", "EQUITY", "DERIVATIVES"]

SEGMENT_TO_SYMBOLS = {
    "INDEX": ["NIFTY", "BANKNIFTY"],
    "EQUITY": ["RELIANCE", "TCS"],
    "DERIVATIVES": ["NIFTY OPTIONS", "BANKNIFTY OPTIONS"],
}

SEGMENT_TO_EXCHANGE_SEGMENT = {
    "INDEX": "IDX_I",
    "EQUITY": "NSE_EQ",
}

# ---------------- SECURITY ID MAP (required by Dhan) ----------------
SECURITY_MAP = {
    "NIFTY": 13,
    "BANKNIFTY": 25,
    "RELIANCE": 2885,
    "TCS": 11536,
}

DERIV_UNDERLYING_MAP = {
    "NIFTY OPTIONS": "NIFTY",
    "BANKNIFTY OPTIONS": "BANKNIFTY",
}

# ---------------- MOCK DATA (fallback) ----------------
def mock_ltp(segment: str, symbol: str) -> float:
    base = {
        "NIFTY": 22500.0,
        "BANKNIFTY": 48500.0,
        "RELIANCE": 2950.0,
        "TCS": 4150.0,
        "NIFTY OPTIONS": 22500.0,
        "BANKNIFTY OPTIONS": 48500.0,
    }.get(symbol, 100.0)
    return round(base + (time.time() % 10) - 5, 2)

def mock_option_chain(underlying: str) -> list[dict]:
    spot = mock_ltp("DERIVATIVES", underlying)
    atm = int(round(spot / 50.0) * 50)
    rows = []
    for i in range(-8, 9):
        strike = atm + i * 50
        ce_ltp = max(0.5, round(max(0, (spot - strike)) * 0.6 + (9 - abs(i)) * 2.0, 2))
        pe_ltp = max(0.5, round(max(0, (strike - spot)) * 0.6 + (9 - abs(i)) * 2.0, 2))
        rows.append(
            {
                "strike": strike,
                "ce_ltp": ce_ltp,
                "ce_oi": 100000 + (i + 10) * 1200,
                "pe_ltp": pe_ltp,
                "pe_oi": 98000 + (10 - i) * 1100,
            }
        )
    return rows

def mock_expiries(symbol: str) -> list[str]:
    today = datetime.now(timezone.utc).date()
    expiries = []
    d = today
    while len(expiries) < 3:
        d = d.fromordinal(d.toordinal() + 1)
        if d.weekday() == 3:
            expiries.append(d.isoformat())
    return expiries

# ---------------- DHAN API HELPERS ----------------
def _have_dhan_creds() -> bool:
    return bool(CLIENT_ID) and bool(ACCESS_TOKEN)

def _safe_post(url: str, payload: dict) -> dict:
    resp = requests.post(
        url,
        json=payload,
        headers=DHAN_HEADERS,
        timeout=REQUEST_TIMEOUT_SECS,
    )

    # REQUIRED logging
    logger.info("API RESPONSE: %s", resp.text)

    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")

    try:
        return resp.json()
    except Exception as e:
        raise RuntimeError(f"Invalid JSON from {url}: {e}") from e


def _resolve_underlying(symbol: str) -> str:
    return DERIV_UNDERLYING_MAP.get(symbol, symbol)

def dhan_ltp(segment: str, symbol: str) -> float:
    """Correct Dhan LTP using securityId mapping.

    Payload examples required:
      {"IDX_I": [13]}
      {"NSE_EQ": [2885]}

    Raises on failure; caller will fall back to mock.
    """
    if not _have_dhan_creds():
        raise RuntimeError("Missing CLIENT_ID / DHAN_ACCESS_TOKEN")

    base_symbol = _resolve_underlying(symbol)

    if segment == "DERIVATIVES":
        # Derivatives LTP shown as underlying spot; treat as index segment
        segment = "INDEX"

    exch_seg = SEGMENT_TO_EXCHANGE_SEGMENT.get(segment)
    if not exch_seg:
        raise RuntimeError(f"Unsupported segment for LTP: {segment}")

    security_id = SECURITY_MAP.get(base_symbol)
    if not security_id:
        raise RuntimeError(f"No securityId mapping for symbol: {base_symbol}")

    payload = {exch_seg: [security_id]}
    data = _safe_post(DHAN_LTP_URL, payload)

    # Typical shape from earlier code: {"data":[{...}]} but may vary.
    if isinstance(data, dict):
        d = data.get("data")
        if isinstance(d, list) and d:
            row = d[0]
            for k in ("lastPrice", "ltp", "LTP", "last_price"):
                if k in row and row.get(k) is not None:
                    return float(row.get(k))

    raise RuntimeError(f"Unexpected LTP response shape: {json.dumps(data)[:300]}")

def dhan_expiries(deriv_symbol: str) -> list[str]:
    """Correct Dhan expiries using UnderlyingScrip/UnderlyingSeg payload."""
    if not _have_dhan_creds():
        raise RuntimeError("Missing CLIENT_ID / DHAN_ACCESS_TOKEN")

    underlying = _resolve_underlying(deriv_symbol)
    security_id = SECURITY_MAP.get(underlying)
    if not security_id:
        raise RuntimeError(f"No securityId mapping for underlying: {underlying}")

    payload = {
        "UnderlyingScrip": security_id,
        "UnderlyingSeg": "IDX_I",  # per your requirement
    }

    data = _safe_post(DHAN_OPTION_EXPIRIES_URL, payload)

    d = data.get("data")
    if isinstance(d, list) and d:
        return [str(x) for x in d]
    if isinstance(d, dict):
        exp = d.get("expiries") or d.get("expiryDates") or d.get("expiry_dates")
        if isinstance(exp, list) and exp:
            return [str(x) for x in exp]

    raise RuntimeError(f"Unexpected expiries response shape: {json.dumps(data)[:300]}")

def dhan_option_chain(deriv_symbol: str, expiry: str) -> list[dict]:
    """Correct Dhan option chain using UnderlyingScrip/UnderlyingSeg payload.

    Minimal required payload (per your instruction):
      {"UnderlyingScrip": 13, "UnderlyingSeg": "IDX_I"}

    Many APIs also require Expiry; we include it when available.
    """
    if not _have_dhan_creds():
        raise RuntimeError("Missing CLIENT_ID / DHAN_ACCESS_TOKEN")

    underlying = _resolve_underlying(deriv_symbol)
    security_id = SECURITY_MAP.get(underlying)
    if not security_id:
        raise RuntimeError(f"No securityId mapping for underlying: {underlying}")

    payload = {
        "UnderlyingScrip": security_id,
        "UnderlyingSeg": "IDX_I",  # per your requirement
        "Expiry": expiry,
    }

    data = _safe_post(DHAN_OPTION_CHAIN_URL, payload)
    d = data.get("data")
    if not d:
        raise RuntimeError("No option chain data")

    # Flexible parsing
    if isinstance(d, list):
        out = []
        for row in d:
            strike = row.get("strike") or row.get("strikePrice") or row.get("strike_price")
            ce = row.get("ce") or row.get("CE") or {}
            pe = row.get("pe") or row.get("PE") or {}
            out.append(
                {
                    "strike": strike,
                    "ce_ltp": ce.get("ltp") or ce.get("lastPrice") or ce.get("last_price"),
                    "ce_oi": ce.get("oi") or ce.get("openInterest") or ce.get("open_interest"),
                    "pe_ltp": pe.get("ltp") or pe.get("lastPrice") or pe.get("last_price"),
                    "pe_oi": pe.get("oi") or pe.get("openInterest") or pe.get("open_interest"),
                }
            )
        return out

    if isinstance(d, dict) and isinstance(d.get("strikes"), list):
        out = []
        for row in d["strikes"]:
            strike = row.get("strike") or row.get("strikePrice") or row.get("strike_price")
            out.append(
                {
                    "strike": strike,
                    "ce_ltp": row.get("ce_ltp"),
                    "ce_oi": row.get("ce_oi"),
                    "pe_ltp": row.get("pe_ltp"),
                    "pe_oi": row.get("pe_oi"),
                }
            )
        return out

    raise RuntimeError(f"Unexpected option chain response shape: {json.dumps(data)[:300]}")


# ---------------- DASH APP ----------------
app = Dash(
    __name__,
    title="AI Trading Dashboard",
    suppress_callback_exceptions=True,
)
server = app.server

# ---------------- UI (NOT inside a function) ----------------
segment_dropdown = dcc.Dropdown(
    id="segment",
    options=[{"label": s, "value": s} for s in SEGMENTS],
    value="INDEX",
    clearable=False,
    persistence=True,
    persistence_type="session",
)

symbol_dropdown = dcc.Dropdown(
    id="symbol",
    options=[{"label": s, "value": s} for s in SEGMENT_TO_SYMBOLS["INDEX"]],
    value=SEGMENT_TO_SYMBOLS["INDEX"][0],
    clearable=False,
    persistence=True,
    persistence_type="session",
)

expiry_dropdown = dcc.Dropdown(
    id="expiry",
    options=[],
    value=None,
    clearable=False,
    placeholder="Select expiry",
    persistence=True,
    persistence_type="session",
)

app.layout = html.Div(
    style={
        "maxWidth": "1100px",
        "margin": "0 auto",
        "padding": "16px",
        "fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, Arial",
    },
    children=[
        html.H1("AI Trading Dashboard (Production)"),
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr", "gap": "12px"},
            children=[
                html.Div([html.Label("Segment"), segment_dropdown]),
                html.Div([html.Label("Symbol"), symbol_dropdown]),
                html.Div(
                    id="expiry-container",
                    children=[html.Label("Expiry (Derivatives only)"), expiry_dropdown],
                    style={"display": "none"},
                ),
            ],
        ),
        html.Hr(),
        html.Div(
            style={"display": "flex", "alignItems": "baseline", "justifyContent": "space-between"},
            children=[
                html.H2(id="ltp", style={"margin": 0}),
                html.Div(id="status", style={"color": "#666", "fontSize": "13px"}),
            ],
        ),
        html.Hr(),
        html.H3("Option Chain"),
        dash_table.DataTable(
            id="option-table",
            columns=[
                {"name": "Strike", "id": "strike", "type": "numeric"},
                {"name": "CE LTP", "id": "ce_ltp", "type": "numeric"},
                {"name": "CE OI", "id": "ce_oi", "type": "numeric"},
                {"name": "PE LTP", "id": "pe_ltp", "type": "numeric"},
                {"name": "PE OI", "id": "pe_oi", "type": "numeric"},
            ],
            data=[],
            page_size=15,
            sort_action="native",
            style_table={"overflowX": "auto"},
            style_cell={"padding": "8px", "whiteSpace": "nowrap"},
            style_header={"fontWeight": "600"},
        ),
        dcc.Interval(id="interval", interval=3000, n_intervals=0),
        dcc.Store(id="expiry-cache", storage_type="memory"),
    ],
)

print("LAYOUT LOADED")


# (A) Update SYMBOL based on SEGMENT
@app.callback(
    Output("symbol", "options"),
    Output("symbol", "value"),
    Input("segment", "value"),
)
def update_symbol_dropdown(segment: str):
    symbols = SEGMENT_TO_SYMBOLS.get(segment, [])
    options = [{"label": s, "value": s} for s in symbols]
    value = symbols[0] if symbols else None
    return options, value


# (B) Show EXPIRY only when DERIVATIVES selected
@app.callback(
    Output("expiry-container", "style"),
    Input("segment", "value"),
)
def toggle_expiry(segment: str):
    if segment == "DERIVATIVES":
        return {"display": "block"}
    return {"display": "none"}

@app.callback(
    Output("expiry", "options"),
    Output("expiry", "value"),
    Output("expiry-cache", "data"),
    Input("segment", "value"),
    Input("symbol", "value"),
    State("expiry-cache", "data"),
)
def update_expiry_dropdown(segment: str, symbol: str, cache):
    if segment != "DERIVATIVES":
        return [], None, cache

    if not symbol:
        return [], None, cache

    cache = cache or {}
    cached = cache.get(symbol)
    if cached and isinstance(cached, dict) and "expiries" in cached:
        expiries = cached["expiries"]
        opts = [{"label": e, "value": e} for e in expiries]
        val = expiries[0] if expiries else None
        return opts, val, cache

    try:
        expiries = dhan_expiries(symbol)
        if not expiries:
            raise RuntimeError("Empty expiries list")
        cache[symbol] = {"expiries": expiries, "ts": time.time()}
    except Exception as e:
        logger.error(f"Expiry fetch failed for {symbol}: {e}")
        expiries = mock_expiries(symbol)
        cache[symbol] = {"expiries": expiries, "ts": time.time(), "mock": True}

    opts = [{"label": e, "value": e} for e in expiries]
    val = expiries[0] if expiries else None
    return opts, val, cache

@app.callback(
    Output("ltp", "children"),
    Output("option-table", "data"),
    Output("status", "children"),
    Input("interval", "n_intervals"),
    Input("segment", "value"),
    Input("symbol", "value"),
    Input("expiry", "value"),
)
def update_dashboard(n, segment: str, symbol: str, expiry: str):
    logger.info("CALLBACK RUNNING")

    if not segment or not symbol:
        raise PreventUpdate

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_bits = [f"refreshed: {now}", f"segment: {segment}", f"symbol: {symbol}"]

    ltp_value = None
    ltp_source = "dhan"
    try:
        ltp_value = dhan_ltp(segment, symbol)
    except Exception as e:
        logger.error(f"LTP fetch failed for {segment}/{symbol}: {e}")
        ltp_value = mock_ltp(segment, symbol)
        ltp_source = "mock"

    ltp_text = f"{symbol} LTP: {ltp_value} ({ltp_source})"
    status_bits.append(f"ltp: {ltp_source}")

    if segment != "DERIVATIVES":
        return ltp_text, [], " | ".join(status_bits)

    if not expiry:
        status_bits.append("expiry: none")
        return ltp_text, [], " | ".join(status_bits)

    status_bits.append(f"expiry: {expiry}")

    chain_source = "dhan"
    try:
        rows = dhan_option_chain(symbol, expiry)
        df = pd.DataFrame(rows)
        for col in ["strike", "ce_ltp", "ce_oi", "pe_ltp", "pe_oi"]:
            if col not in df.columns:
                df[col] = None
        df = df[["strike", "ce_ltp", "ce_oi", "pe_ltp", "pe_oi"]].copy()
        for col in ["strike", "ce_ltp", "ce_oi", "pe_ltp", "pe_oi"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.sort_values("strike", ascending=True)
        table_data = df.fillna("").to_dict("records")
    except Exception as e:
        logger.error(f"Option chain fetch failed for {symbol} expiry={expiry}: {e}")
        chain_source = "mock"
        table_data = mock_option_chain(symbol)

    status_bits.append(f"chain: {chain_source}")
    return ltp_text, table_data, " | ".join(status_bits)


print("CALLBACK REGISTERED")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)