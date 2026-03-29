import logging
import os
import sys
import traceback
from datetime import datetime
import requests
import pandas as pd
import plotly.graph_objs as go
from dash import Dash, html, dcc, dash_table, Input, Output, State
import dash_bootstrap_components as dbc

# ---------- LOGGING ----------
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("app")

# ---------- ENV ----------
CLIENT_ID = os.getenv("CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
PORT = int(os.environ.get("PORT", 3000))

HEADERS = {
    "access-token": DHAN_ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

log.info("🚀 DASH APP STARTING")
log.info("CLIENT_ID: %s", CLIENT_ID or "MISSING")
log.info("DHAN_ACCESS_TOKEN: %s", "OK" if DHAN_ACCESS_TOKEN else "MISSING")

# ---------- API ----------
LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
EXPIRY_URL = "https://api.dhan.co/v2/optionChain/expiryList"
OPTION_CHAIN_URL = "https://api.dhan.co/v2/optionChain"

# ---------- SETTINGS ----------
LTP_INTERVAL_MS = 1000
OC_INTERVAL_MS = 5000
MAX_POINTS = 100

# ---------- FALLBACK ----------
def mock_ltp():
    return 22500 + (datetime.now().second % 50)

def mock_oc():
    return [
        {"Strike": 22400, "CE LTP": 120, "PE LTP": 80, "CE OI": 100000, "PE OI": 90000},
        {"Strike": 22500, "CE LTP": 90, "PE LTP": 100, "CE OI": 120000, "PE OI": 110000},
        {"Strike": 22600, "CE LTP": 60, "PE LTP": 130, "CE OI": 90000, "PE OI": 140000},
    ]

# ---------- API CALLS ----------
def fetch_ltp():
    """Fetch last traded price for NIFTY (security ID 13) via Dhan LTP API.

    Returns the live price on success, or mock data on any failure.
    Detects 401 Unauthorized explicitly and logs all errors to stdout.
    """
    try:
        payload = {"NSE_INDEX": [13]}
        log.info("LTP → POST %s | payload=%s", LTP_URL, payload)
        res = SESSION.post(LTP_URL, json=payload, timeout=5)

        log.info("LTP ← status=%d | body=%s", res.status_code, res.text[:500])

        if res.status_code == 401:
            log.error(
                "LTP ← 401 Unauthorized — token is invalid or expired. "
                "Update DHAN_ACCESS_TOKEN in Railway environment variables."
            )
            log.warning("⚠️ LTP: falling back to mock data (401)")
            return mock_ltp(), True

        if res.status_code >= 400:
            log.error("LTP ← HTTP %d error — %s", res.status_code, res.text[:500])
            log.warning("⚠️ LTP: falling back to mock data (HTTP %d)", res.status_code)
            return mock_ltp(), True

        data = res.json()
        # Dhan v2 LTP response: {"data": {"NSE_INDEX": {"13": {"last_price": ...}}}}
        # or list form: {"data": [{"lastPrice": ...}]}
        price = None
        raw_data = data.get("data", {})
        if isinstance(raw_data, list) and raw_data:
            price = raw_data[0].get("lastPrice") or raw_data[0].get("last_price")
        elif isinstance(raw_data, dict):
            # Nested segment → security_id → record
            for seg_val in raw_data.values():
                if isinstance(seg_val, dict):
                    for record in seg_val.values():
                        if isinstance(record, dict):
                            price = record.get("last_price") or record.get("lastPrice")
                            break
                if price is not None:
                    break

        if price is None:
            log.error("LTP ← price field missing in response: %s", data)
            log.warning("⚠️ LTP: falling back to mock data (no price field)")
            return mock_ltp(), True

        log.info("LTP ← price=%.2f ✅", float(price))
        return float(price), False

    except requests.exceptions.Timeout:
        log.error("LTP ← request timed out after 5s")
        log.warning("⚠️ LTP: falling back to mock data (timeout)")
        return mock_ltp(), True
    except Exception as e:
        log.error("LTP ← unexpected error: %s\n%s", e, traceback.format_exc())
        log.warning("⚠️ LTP: falling back to mock data (exception)")
        return mock_ltp(), True


def fetch_expiry():
    """Fetch the nearest expiry code for NIFTY from Dhan option chain expiry API.

    Returns (expiry_code, is_error). Falls back to a safe placeholder on failure.
    """
    FALLBACK_EXPIRY = "2025-01-30"
    try:
        params = {"UnderlyingScrip": 13, "UnderlyingSeg": "IDX_I"}
        log.info("EXPIRY → GET %s | params=%s", EXPIRY_URL, params)
        res = SESSION.get(EXPIRY_URL, params=params, timeout=5)

        log.info("EXPIRY ← status=%d | body=%s", res.status_code, res.text[:500])

        if res.status_code == 401:
            log.error(
                "EXPIRY ← 401 Unauthorized — token is invalid or expired."
            )
            return FALLBACK_EXPIRY, True

        if res.status_code >= 400:
            log.error("EXPIRY ← HTTP %d error — %s", res.status_code, res.text[:500])
            return FALLBACK_EXPIRY, True

        body = res.json()
        data = body.get("data", [])
        if not data:
            log.error("EXPIRY ← empty data in response: %s", body)
            return FALLBACK_EXPIRY, True

        # Accept list of strings or list of dicts with an expiryCode key
        first = data[0]
        if isinstance(first, dict):
            expiry = first.get("expiryCode") or first.get("expiry") or first.get("ExpiryCode")
        else:
            expiry = str(first)

        if not expiry:
            log.error("EXPIRY ← could not extract expiry code from: %s", first)
            return FALLBACK_EXPIRY, True

        log.info("EXPIRY ← expiry=%s ✅", expiry)
        return str(expiry), False

    except requests.exceptions.Timeout:
        log.error("EXPIRY ← request timed out after 5s")
        return FALLBACK_EXPIRY, True
    except Exception as e:
        log.error("EXPIRY ← unexpected error: %s\n%s", e, traceback.format_exc())
        return FALLBACK_EXPIRY, True


def fetch_option_chain():
    """Fetch NIFTY option chain from Dhan API using GET with query parameters.

    Returns (rows, is_error). Always returns at least mock data so the table
    is never blank.
    """
    expiry, expiry_err = fetch_expiry()

    try:
        params = {
            "UnderlyingScrip": 13,
            "UnderlyingSeg": "IDX_I",
            "Expiry": expiry,
        }
        log.info("OC → GET %s | params=%s", OPTION_CHAIN_URL, params)
        res = SESSION.get(OPTION_CHAIN_URL, params=params, timeout=5)

        log.info("OC ← status=%d | body=%s", res.status_code, res.text[:500])

        if res.status_code == 401:
            log.error(
                "OC ← 401 Unauthorized — token is invalid or expired. "
                "Update DHAN_ACCESS_TOKEN in Railway environment variables."
            )
            log.warning("⚠️ OC: falling back to mock data (401)")
            return mock_oc(), True

        if res.status_code >= 400:
            log.error("OC ← HTTP %d error — %s", res.status_code, res.text[:500])
            log.warning("⚠️ OC: falling back to mock data (HTTP %d)", res.status_code)
            return mock_oc(), True

        body = res.json()
        data = body.get("data")

        if not data:
            log.error("OC ← empty data in response: %s", body)
            log.warning("⚠️ OC: falling back to mock data (no data field)")
            return mock_oc(), True

        # data may be a list of strike records or a dict with an "oc" key
        if isinstance(data, dict):
            chain = data.get("oc") or data.get("records") or data.get("chain") or []
        elif isinstance(data, list):
            chain = data
        else:
            log.error("OC ← unexpected data shape: %s", type(data))
            return mock_oc(), True

        rows = []
        for item in chain[:20]:
            if not isinstance(item, dict):
                continue
            ce = item.get("CE") or item.get("ce") or {}
            pe = item.get("PE") or item.get("pe") or {}
            rows.append({
                "Strike": item.get("strikePrice") or item.get("strike_price") or item.get("strike"),
                "CE LTP": ce.get("ltp") or ce.get("lastPrice") or ce.get("last_price"),
                "PE LTP": pe.get("ltp") or pe.get("lastPrice") or pe.get("last_price"),
                "CE OI": ce.get("oi") or ce.get("openInterest"),
                "PE OI": pe.get("oi") or pe.get("openInterest"),
            })

        if not rows:
            log.warning("OC ← chain parsed but produced 0 rows; falling back to mock data")
            return mock_oc(), True

        log.info("OC ← %d rows parsed ✅", len(rows))
        return rows, expiry_err

    except requests.exceptions.Timeout:
        log.error("OC ← request timed out after 5s")
        log.warning("⚠️ OC: falling back to mock data (timeout)")
        return mock_oc(), True
    except Exception as e:
        log.error("OC ← unexpected error: %s\n%s", e, traceback.format_exc())
        log.warning("⚠️ OC: falling back to mock data (exception)")
        return mock_oc(), True

# ---------- DASH APP ----------
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

app.layout = dbc.Container([
    html.H2("🔥 AI Trading Dashboard"),
    dbc.Alert("Waiting...", id="status", color="secondary"),
    dbc.Alert("", id="api-error", color="warning", is_open=False),
    html.H3(id="ltp"),
    dcc.Graph(id="chart"),
    dash_table.DataTable(
        id="table",
        columns=[
            {"name": "Strike", "id": "Strike"},
            {"name": "CE LTP", "id": "CE LTP"},
            {"name": "PE LTP", "id": "PE LTP"},
            {"name": "CE OI", "id": "CE OI"},
            {"name": "PE OI", "id": "PE OI"},
        ],
        page_size=10,
        style_table={"overflowX": "auto"},
    ),
    dcc.Store(id="history", data=[]),
    dcc.Store(id="ltp-error", data=False),
    dcc.Interval(id="ltp-interval", interval=LTP_INTERVAL_MS),
    dcc.Interval(id="oc-interval", interval=OC_INTERVAL_MS),
], fluid=True)

# ---------- LTP CALLBACK ----------
@app.callback(
    Output("ltp", "children"),
    Output("status", "children"),
    Output("status", "color"),
    Output("chart", "figure"),
    Output("history", "data"),
    Output("ltp-error", "data"),
    Input("ltp-interval", "n_intervals"),
    State("history", "data"),
)
def update_ltp(n, history):
    price, is_error = fetch_ltp()
    ts = datetime.now().strftime("%H:%M:%S")

    history = history or []
    history.append({"time": ts, "price": price})
    history = history[-MAX_POINTS:]

    df = pd.DataFrame(history)

    fig = go.Figure(
        data=[go.Scatter(x=df["time"], y=df["price"], mode="lines")],
        layout=go.Layout(template="plotly_dark", title="LTP"),
    )

    if is_error:
        status_msg = f"⚠️ API Error — Using Mock Data | {ts}"
        status_color = "warning"
    else:
        status_msg = f"✅ LIVE | {ts}"
        status_color = "success"

    return f"LTP: {price:.2f}", status_msg, status_color, fig, history, is_error

# ---------- OC CALLBACK ----------
@app.callback(
    Output("table", "data"),
    Output("api-error", "children"),
    Output("api-error", "is_open"),
    Input("oc-interval", "n_intervals"),
    State("ltp-error", "data"),
)
def update_oc(n, ltp_is_error):
    rows, is_error = fetch_option_chain()

    # Guarantee the table always has data
    if not rows:
        rows = mock_oc()
        is_error = True

    if is_error or ltp_is_error:
        error_msg = (
            "⚠️ API Error — Displaying mock/fallback data. "
            "Check DHAN_ACCESS_TOKEN and CLIENT_ID in Railway environment variables."
        )
        return rows, error_msg, True

    return rows, "", False

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)

