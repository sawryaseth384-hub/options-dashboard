import os
import logging
from datetime import datetime
import requests
import pandas as pd
import plotly.graph_objs as go
from dash import Dash, html, dcc, dash_table, Input, Output, State
import dash_bootstrap_components as dbc

# ---------- LOGGING ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# ---------- ENV ----------
CLIENT_ID = os.getenv("CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
PORT = int(os.environ.get("PORT", 3000))

logging.info("CLIENT_ID present=%s", bool(CLIENT_ID))
logging.info("DHAN_ACCESS_TOKEN present=%s", bool(DHAN_ACCESS_TOKEN))

HEADERS = {
    "access-token": DHAN_ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ---------- API ----------
LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
EXPIRY_URL = "https://api.dhan.co/v2/optionChain/expiryList"
OPTION_CHAIN_URL = "https://api.dhan.co/v2/optionChain"

# ---------- SETTINGS ----------
LTP_INTERVAL_MS = 1000
OC_INTERVAL_MS = 5000
MAX_POINTS = 100
MAX_LOG_CHARS = 500

# ---------- FALLBACK ----------
def mock_ltp():
    return 22500 + (datetime.now().second % 50)

def mock_oc():
    return [
        {"Strike": 22400, "CE LTP": 120, "PE LTP": 80, "CE OI": 100000, "PE OI": 90000},
        {"Strike": 22500, "CE LTP": 90, "PE LTP": 100, "CE OI": 120000, "PE OI": 110000},
        {"Strike": 22600, "CE LTP": 60, "PE LTP": 130, "CE OI": 90000, "PE OI": 140000},
    ]

# ---------- HELPERS ----------
def log_request(name: str, url: str, payload: dict):
    logging.info("%s REQUEST url=%s payload=%s", name, url, payload)

# prints are kept for quick Railway console visibility
# in addition to logging

def log_response(name: str, res: requests.Response):
    body_preview = res.text[:MAX_LOG_CHARS]
    logging.info("%s RESPONSE status=%s", name, res.status_code)
    logging.info("%s RESPONSE body(first %s chars)=%s", name, MAX_LOG_CHARS, body_preview)


def ensure_not_empty(res: requests.Response):
    if not res.text or not res.text.strip():
        raise ValueError("No Data")


def parse_json(res: requests.Response, label: str):
    try:
        return res.json()
    except ValueError:
        raise ValueError(f"{label} invalid JSON")


def parse_price(item: dict):
    for key in ("lastPrice", "ltp", "price"):
        price = item.get(key)
        if price is not None:
            return price
    return None


def map_status_code(status_code: int):
    if status_code == 401:
        return "Invalid Token"
    if status_code == 403:
        return "Access Denied"
    return None

# ---------- API CALL ----------
def fetch_ltp():
    print("FETCH LTP CALLED")
    payload = {"NSE_INDEX": [13]}
    try:
        log_request("LTP", LTP_URL, payload)
        res = SESSION.post(LTP_URL, json=payload, timeout=3)
        log_response("LTP", res)

        msg = map_status_code(res.status_code)
        if msg:
            raise ValueError(msg)
        ensure_not_empty(res)

        data = parse_json(res, "LTP")
        items = data.get("data") or []
        if not items:
            raise ValueError("No Data")

        price = parse_price(items[0])
        if price is None:
            raise ValueError("No price")

        return {"price": price, "used_mock": False, "error": None}

    except Exception as e:
        logging.error("❌ LTP ERROR: %s", e)
        logging.warning("⚠️ USING MOCK LTP")
        return {"price": mock_ltp(), "used_mock": True, "error": str(e)}


def fetch_option_chain():
    print("FETCH OC CALLED")
    try:
        expiry_payload = {"UnderlyingScrip": 13, "UnderlyingSeg": "IDX_I"}
        log_request("EXPIRY", EXPIRY_URL, expiry_payload)
        expiry_res = SESSION.post(EXPIRY_URL, json=expiry_payload, timeout=3)
        log_response("EXPIRY", expiry_res)

        msg = map_status_code(expiry_res.status_code)
        if msg:
            raise ValueError(msg)
        ensure_not_empty(expiry_res)
        expiry_data = parse_json(expiry_res, "Expiry")
        expiry_list = expiry_data.get("data") or []
        if not expiry_list:
            raise ValueError("No Data")
        expiry = expiry_list[0].get("expiryCode")
        if expiry is None:
            raise ValueError("No Expiry Code")

        payload = {
            "UnderlyingScrip": 13,
            "UnderlyingSeg": "IDX_I",
            "ExpiryCode": expiry,
        }

        log_request("OC", OPTION_CHAIN_URL, payload)
        res = SESSION.post(OPTION_CHAIN_URL, json=payload, timeout=3)
        log_response("OC", res)

        msg = map_status_code(res.status_code)
        if msg:
            raise ValueError(msg)
        ensure_not_empty(res)
        data = parse_json(res, "Option Chain").get("data") or []
        if not data:
            raise ValueError("No Data")

        rows = []
        for item in data[:20]:
            rows.append({
                "Strike": item.get("strikePrice"),
                "CE LTP": item.get("CE", {}).get("ltp"),
                "PE LTP": item.get("PE", {}).get("ltp"),
                "CE OI": item.get("CE", {}).get("oi"),
                "PE OI": item.get("PE", {}).get("oi"),
            })

        return {"rows": rows, "used_mock": False, "error": None}

    except Exception as e:
        logging.error("❌ OC ERROR: %s", e)
        logging.warning("⚠️ USING MOCK OC")
        return {"rows": mock_oc(), "used_mock": True, "error": str(e)}

# ---------- DASH APP ----------
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

app.layout = dbc.Container([
    html.H2("🔥 AI Trading Dashboard"),
    dbc.Alert("Waiting...", id="status", color="warning"),
    html.Div(id="ltp"),
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
    ),
    dcc.Store(id="history", data=[]),
    dcc.Interval(id="ltp-interval", interval=LTP_INTERVAL_MS, n_intervals=0),
    dcc.Interval(id="oc-interval", interval=OC_INTERVAL_MS, n_intervals=0),
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
    prevent_initial_call=False,
)
def update_ltp(n, history):
    print("LTP CALLBACK TRIGGERED", n)
    result = fetch_ltp()
    price = result["price"]
    used_mock = result["used_mock"]
    error = result["error"]

    history = history or []
    history.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "price": price
    })
    history = history[-MAX_POINTS:]

    df = pd.DataFrame(history)

    fig = go.Figure(
        data=[go.Scatter(x=df["time"], y=df["price"], mode="lines")],
        layout=go.Layout(template="plotly_dark", title="LTP")
    )

    status_text = "LIVE"
    status_color = "success"
    if error:
        status_text = f"ERROR: {error}" + (" | Using Mock Data" if used_mock else "")
        status_color = "danger"
    elif used_mock:
        status_text = "Using Mock Data"
        status_color = "warning"

    return f"LTP: {price}", status_text, status_color, fig, history

# ---------- OC CALLBACK ----------
@app.callback(
    Output("table", "data"),
    Input("oc-interval", "n_intervals"),
    prevent_initial_call=False,
)
def update_oc(n):
    print("OC CALLBACK TRIGGERED", n)
    result = fetch_option_chain()
    return result["rows"]

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
