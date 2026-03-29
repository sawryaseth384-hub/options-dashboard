import logging
import os
import traceback
from datetime import datetime

import pandas as pd
import plotly.graph_objs as go
import requests
from dash import Dash, Input, Output, State, dash_table, dcc, html
import dash_bootstrap_components as dbc

# ---------- LOGGING ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("options_dashboard")

# ---------- ENV ----------
CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "").strip()
PORT = int(os.environ.get("PORT", 3000))

# Validate credentials at startup and log presence (never log values)
if CLIENT_ID:
    log.info("✅ CLIENT_ID is set (length=%d)", len(CLIENT_ID))
else:
    log.error("❌ CLIENT_ID is NOT set – API calls will fail")

if DHAN_ACCESS_TOKEN:
    log.info("✅ DHAN_ACCESS_TOKEN is set (length=%d)", len(DHAN_ACCESS_TOKEN))
else:
    log.error("❌ DHAN_ACCESS_TOKEN is NOT set – API calls will fail")

_CREDS_OK = bool(CLIENT_ID and DHAN_ACCESS_TOKEN)

# ---------- API ----------
BASE_URL = "https://api.dhan.co/v2"
LTP_URL = f"{BASE_URL}/marketfeed/ltp"
EXPIRY_URL = f"{BASE_URL}/optionChain/expiryList"
OPTION_CHAIN_URL = f"{BASE_URL}/optionChain"

# ---------- SETTINGS ----------
LTP_INTERVAL_MS = 1_000
OC_INTERVAL_MS = 5_000
MAX_POINTS = 100
REQUEST_TIMEOUT = 8  # seconds

# ---------- FALLBACK DATA ----------
def mock_ltp() -> float:
    return 22500 + (datetime.now().second % 50)


def mock_oc() -> list:
    return [
        {"Strike": 22400, "CE LTP": 120, "PE LTP": 80,  "CE OI": 100_000, "PE OI": 90_000},
        {"Strike": 22500, "CE LTP": 90,  "PE LTP": 100, "CE OI": 120_000, "PE OI": 110_000},
        {"Strike": 22600, "CE LTP": 60,  "PE LTP": 130, "CE OI": 90_000,  "PE OI": 140_000},
    ]


# ---------- HTTP SESSION ----------
def _build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    return s


SESSION = _build_session()


def _safe_request(method: str, url: str, **kwargs) -> tuple:
    """
    Perform an HTTP request and return (response, error_string).
    Handles network errors, timeouts, and auth failures explicitly.
    Returns (None, error_msg) on any failure.
    """
    log.info("→ %s %s  kwargs=%s", method.upper(), url,
             {k: v for k, v in kwargs.items() if k != "json"})
    if kwargs.get("json"):
        log.info("  payload: %s", kwargs["json"])

    try:
        res = SESSION.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
    except requests.exceptions.Timeout:
        msg = f"Request timeout after {REQUEST_TIMEOUT}s – {url}"
        log.error("❌ %s", msg)
        return None, msg
    except requests.exceptions.ConnectionError as exc:
        msg = f"Connection failed – {url}: {exc}"
        log.error("❌ %s", msg)
        return None, msg
    except Exception as exc:
        msg = f"Unexpected network error – {url}: {exc}"
        log.error("❌ %s\n%s", msg, traceback.format_exc())
        return None, msg

    log.info("← HTTP %d  url=%s  body_preview=%.500s",
             res.status_code, url, res.text)

    if res.status_code == 401:
        msg = "HTTP 401 Unauthorized – DHAN_ACCESS_TOKEN is invalid or expired"
        log.error("❌ %s", msg)
        return None, msg

    if res.status_code == 403:
        msg = "HTTP 403 Forbidden – access denied; check CLIENT_ID and token permissions"
        log.error("❌ %s", msg)
        return None, msg

    if res.status_code >= 400:
        msg = f"HTTP {res.status_code} error – {res.text[:300]}"
        log.error("❌ %s", msg)
        return None, msg

    return res, None


def _parse_json(res: requests.Response, context: str) -> tuple:
    """Parse JSON from a response. Returns (data, error_string)."""
    try:
        return res.json(), None
    except Exception as exc:
        msg = f"Invalid JSON response in {context}: {exc} – raw='{res.text[:300]}'"
        log.error("❌ %s", msg)
        return None, msg


# ---------- fetch_ltp ----------
def fetch_ltp() -> tuple:
    """
    Fetch NIFTY LTP from Dhan v2 marketfeed/ltp.
    Returns (price: float, is_error: bool).
    Falls back to mock_ltp() on any failure.
    """
    if not _CREDS_OK:
        log.warning("⚠️ Skipping LTP fetch – credentials missing; using mock data")
        return mock_ltp(), True

    payload = {"NSE_INDEX": [13]}
    res, err = _safe_request("POST", LTP_URL, json=payload)
    if err:
        log.warning("⚠️ LTP fetch failed (%s); falling back to mock data", err)
        return mock_ltp(), True

    data, err = _parse_json(res, "fetch_ltp")
    if err:
        log.warning("⚠️ LTP JSON parse failed; falling back to mock data")
        return mock_ltp(), True

    # Try multiple response shapes
    price = None
    try:
        # Shape 1: {"data": [{"lastPrice": ...}]}
        inner = data.get("data") if isinstance(data, dict) else data
        if isinstance(inner, list) and inner:
            record = inner[0]
            price = (
                record.get("lastPrice")
                or record.get("ltp")
                or record.get("last_price")
                or record.get("price")
            )
        # Shape 2: {"data": {"NSE_INDEX": {"13": {"lastPrice": ...}}}}
        elif isinstance(inner, dict):
            for seg_data in inner.values():
                if isinstance(seg_data, dict):
                    for rec in seg_data.values():
                        if isinstance(rec, dict):
                            price = (
                                rec.get("lastPrice")
                                or rec.get("ltp")
                                or rec.get("last_price")
                            )
                            if price:
                                break
                if price:
                    break
    except Exception as exc:
        log.error("❌ Field extraction failed in fetch_ltp: %s\n%s",
                  exc, traceback.format_exc())

    if price is None:
        log.warning("⚠️ LTP field not found in response (keys=%s); falling back to mock",
                    list(data.keys()) if isinstance(data, dict) else type(data))
        return mock_ltp(), True

    try:
        price = float(price)
    except (TypeError, ValueError) as exc:
        log.error("❌ LTP value '%s' is not numeric: %s; falling back to mock", price, exc)
        return mock_ltp(), True

    log.info("✅ LTP fetched successfully: %.2f", price)
    return price, False


# ---------- fetch_expiry ----------
def fetch_expiry() -> tuple:
    """
    Fetch the nearest expiry code for NIFTY from Dhan v2 optionChain/expiryList.
    Returns (expiry_code: str, is_error: bool).
    Falls back to a safe default string on failure.
    """
    _FALLBACK_EXPIRY = "nearest"

    if not _CREDS_OK:
        log.warning("⚠️ Skipping expiry fetch – credentials missing; using fallback")
        return _FALLBACK_EXPIRY, True

    payload = {"UnderlyingScrip": 13, "UnderlyingSeg": "IDX_I"}
    res, err = _safe_request("POST", EXPIRY_URL, json=payload)
    if err:
        log.warning("⚠️ Expiry fetch failed (%s); using fallback '%s'", err, _FALLBACK_EXPIRY)
        return _FALLBACK_EXPIRY, True

    data, err = _parse_json(res, "fetch_expiry")
    if err:
        log.warning("⚠️ Expiry JSON parse failed; using fallback '%s'", _FALLBACK_EXPIRY)
        return _FALLBACK_EXPIRY, True

    expiry_code = None
    try:
        inner = data.get("data") if isinstance(data, dict) else data
        # Shape 1: {"data": [{"expiryCode": "..."}]}
        if isinstance(inner, list) and inner:
            first = inner[0]
            expiry_code = (
                first.get("expiryCode")
                or first.get("expiry")
                or first.get("expiryDate")
                or (str(first) if isinstance(first, (int, str)) else None)
            )
        # Shape 2: {"data": ["2024-01-25", ...]}  (plain list of strings/ints)
        elif isinstance(inner, list) and inner:
            expiry_code = str(inner[0])
        # Shape 3: {"data": {"expiries": [...]}}
        elif isinstance(inner, dict):
            for key in ("expiries", "expiryList", "expiry", "items"):
                val = inner.get(key)
                if isinstance(val, list) and val:
                    expiry_code = str(val[0])
                    break
    except Exception as exc:
        log.error("❌ Field extraction failed in fetch_expiry: %s\n%s",
                  exc, traceback.format_exc())

    if not expiry_code:
        log.warning("⚠️ Expiry code not found in response; using fallback '%s'", _FALLBACK_EXPIRY)
        return _FALLBACK_EXPIRY, True

    log.info("✅ Expiry fetched successfully: %s", expiry_code)
    return str(expiry_code), False


# ---------- fetch_option_chain ----------
def fetch_option_chain() -> tuple:
    """
    Fetch NIFTY option chain from Dhan v2 optionChain.
    Returns (rows: list[dict], is_error: bool).
    Guarantees rows is never empty – falls back to mock_oc() on any failure.
    """
    if not _CREDS_OK:
        log.warning("⚠️ Skipping option chain fetch – credentials missing; using mock data")
        return mock_oc(), True

    expiry_code, expiry_err = fetch_expiry()

    payload = {
        "UnderlyingScrip": 13,
        "UnderlyingSeg": "IDX_I",
        "Expiry": expiry_code,
    }
    res, err = _safe_request("POST", OPTION_CHAIN_URL, json=payload)
    if err:
        log.warning("⚠️ Option chain fetch failed (%s); using mock data", err)
        return mock_oc(), True

    data, err = _parse_json(res, "fetch_option_chain")
    if err:
        log.warning("⚠️ Option chain JSON parse failed; using mock data")
        return mock_oc(), True

    rows = []
    try:
        inner = data.get("data") if isinstance(data, dict) else data

        # Shape 1: {"data": [{"strikePrice": ..., "CE": {...}, "PE": {...}}]}
        if isinstance(inner, list):
            chain_list = inner
        # Shape 2: {"data": {"oc": {"22500": {"CE": {...}, "PE": {...}}}}}
        elif isinstance(inner, dict):
            chain_list = None
            for key in ("oc", "records", "chain", "optionChain"):
                val = inner.get(key)
                if isinstance(val, list):
                    chain_list = val
                    break
                if isinstance(val, dict):
                    # dict keyed by strike price
                    chain_list = []
                    for strike_str, row in val.items():
                        entry = dict(row)
                        entry.setdefault("strikePrice", strike_str)
                        chain_list.append(entry)
                    break
            if chain_list is None:
                # Treat the dict itself as a single record or give up
                log.warning("⚠️ Unrecognised option chain structure (keys=%s); using mock",
                            list(inner.keys()))
                return mock_oc(), True
        else:
            log.warning("⚠️ Option chain data is neither list nor dict (type=%s); using mock",
                        type(inner))
            return mock_oc(), True

        for item in chain_list[:20]:
            if not isinstance(item, dict):
                continue
            ce = item.get("CE") or item.get("ce") or item.get("call") or {}
            pe = item.get("PE") or item.get("pe") or item.get("put") or {}
            strike = (
                item.get("strikePrice")
                or item.get("strike")
                or item.get("strike_price")
            )
            rows.append({
                "Strike": strike,
                "CE LTP": ce.get("ltp") or ce.get("lastPrice") or ce.get("last_price"),
                "PE LTP": pe.get("ltp") or pe.get("lastPrice") or pe.get("last_price"),
                "CE OI":  ce.get("oi")  or ce.get("openInterest"),
                "PE OI":  pe.get("oi")  or pe.get("openInterest"),
            })

    except Exception as exc:
        log.error("❌ Option chain parsing failed: %s\n%s", exc, traceback.format_exc())
        return mock_oc(), True

    if not rows:
        log.warning("⚠️ Option chain parsed 0 rows; using mock data")
        return mock_oc(), True

    log.info("✅ Option chain fetched successfully: %d rows (expiry=%s, expiry_err=%s)",
             len(rows), expiry_code, expiry_err)
    return rows, expiry_err  # propagate expiry error flag if expiry was mocked


# ---------- DASH APP ----------
log.info("🚀 Starting Options Dashboard on port %d", PORT)

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

_CREDS_ALERT = dbc.Alert(
    "⚠️ API Error – Check DHAN_ACCESS_TOKEN and CLIENT_ID in Railway environment variables",
    id="creds-alert",
    color="danger",
    is_open=not _CREDS_OK,
    dismissable=True,
)

app.layout = dbc.Container([
    html.H2("🔥 AI Trading Dashboard"),
    _CREDS_ALERT,
    dbc.Alert("Initialising…", id="status", color="secondary"),
    dbc.Alert("", id="api-error-alert", color="warning", is_open=False, dismissable=True),
    html.H3(id="ltp"),
    dcc.Graph(id="chart"),
    dash_table.DataTable(
        id="table",
        columns=[
            {"name": "Strike", "id": "Strike"},
            {"name": "CE LTP",  "id": "CE LTP"},
            {"name": "PE LTP",  "id": "PE LTP"},
            {"name": "CE OI",   "id": "CE OI"},
            {"name": "PE OI",   "id": "PE OI"},
        ],
        page_size=10,
        style_table={"overflowX": "auto"},
    ),
    dcc.Store(id="history", data=[]),
    dcc.Interval(id="ltp-interval", interval=LTP_INTERVAL_MS),
    dcc.Interval(id="oc-interval",  interval=OC_INTERVAL_MS),
], fluid=True)


# ---------- LTP CALLBACK ----------
@app.callback(
    Output("ltp", "children"),
    Output("status", "children"),
    Output("status", "color"),
    Output("chart", "figure"),
    Output("history", "data"),
    Input("ltp-interval", "n_intervals"),
    State("history", "data"),
)
def update_ltp(n, history):
    price, is_error = fetch_ltp()
    now = datetime.now().strftime("%H:%M:%S")

    history = history or []
    history.append({"time": now, "price": price})
    history = history[-MAX_POINTS:]

    df = pd.DataFrame(history)
    fig = go.Figure(
        data=[go.Scatter(x=df["time"], y=df["price"], mode="lines")],
        layout=go.Layout(template="plotly_dark", title="NIFTY LTP"),
    )

    if is_error:
        status_text = f"⚠️ API Error – Check Dhan credentials | {now}"
        status_color = "warning"
    else:
        status_text = f"✅ LIVE | {now}"
        status_color = "success"

    return f"LTP: {price:.2f}", status_text, status_color, fig, history


# ---------- OC CALLBACK ----------
@app.callback(
    Output("table", "data"),
    Output("api-error-alert", "children"),
    Output("api-error-alert", "is_open"),
    Input("oc-interval", "n_intervals"),
)
def update_oc(n):
    rows, is_error = fetch_option_chain()

    if is_error:
        alert_msg = (
            "⚠️ API Error – Check DHAN_ACCESS_TOKEN and CLIENT_ID "
            "in Railway environment variables"
        )
        return rows, alert_msg, True

    return rows, "", False


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)

