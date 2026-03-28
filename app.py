import os
import time
from datetime import datetime
import requests
import pandas as pd
import plotly.graph_objs as go
from dash import Dash, html, dcc, dash_table, Input, Output, State
import dash_bootstrap_components as dbc

# ---------- ENV ----------
CLIENT_ID = os.getenv("CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
PORT = int(os.environ.get("PORT", 3000))

print("✅ APP STARTED")
print("CLIENT:", CLIENT_ID)
print("TOKEN:", "OK" if DHAN_ACCESS_TOKEN else "MISSING")

HEADERS = {
    "access-token": DHAN_ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
}

# ---------- API ----------
LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
EXPIRY_URL = "https://api.dhan.co/v2/optionChain/expiryList"
OPTION_CHAIN_URL = "https://api.dhan.co/v2/optionChain"

UNDERLYINGS = {"NIFTY": {"id": 13, "segment": "IDX_I"}}

# ---------- SETTINGS ----------
LTP_INTERVAL_MS = 1000
OC_INTERVAL_MS = 8000
REQUEST_TIMEOUT = 3
MAX_POINTS = 150

# ---------- CACHE ----------
option_cache = {"data": [], "time": 0}
expiry_cache = {"code": None, "time": 0}

# ---------- HELPERS ----------
def fetch_ltp():
    try:
        payload = {"NSE_INDEX": [UNDERLYINGS["NIFTY"]["id"]]}
        r = requests.post(LTP_URL, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json().get("data", {})

        if isinstance(data, list) and data:
            price = data[0].get("ltp") or data[0].get("lastPrice")
            return float(price), None if price else (None, "No LTP price")

        return None, "No LTP data"
    except Exception as e:
        return None, str(e)

def fetch_expiry():
    try:
        payload = {
            "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
            "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
        }
        r = requests.post(EXPIRY_URL, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json().get("data", [])

        if not data:
            return None, "Empty expiry"

        return data[0].get("expiryCode"), None
    except Exception as e:
        return None, str(e)

def fetch_option_chain():
    expiry, err = fetch_expiry()
    if err:
        return [], err

    try:
        payload = {
            "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
            "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
            "ExpiryCode": expiry,
        }
        r = requests.post(OPTION_CHAIN_URL, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json().get("data", [])

        if not data:
            return [], "Empty option chain"

        rows = []
        for item in data:
            rows.append({
                "Strike": item.get("strikePrice"),
                "CE LTP": item.get("CE", {}).get("ltp"),
                "PE LTP": item.get("PE", {}).get("ltp"),
            })

        return rows, None
    except Exception as e:
        return [], str(e)

def build_chart(history):
    try:
        if not history:
            return go.Figure(layout=go.Layout(template="plotly_dark", title="Live LTP"))

        df = pd.DataFrame(history)

        if "time" not in df or "price" not in df:
            return go.Figure()

        return go.Figure(
            data=[go.Scatter(x=df["time"], y=df["price"], mode="lines")],
            layout=go.Layout(template="plotly_dark", title="Live LTP"),
        )
    except Exception as e:
        print("Chart error:", e)
        return go.Figure()

# ---------- APP ----------
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True,
    prevent_initial_callbacks="initial_duplicate"
)

server = app.server

# ---------- LAYOUT ----------
app.layout = dbc.Container([
    html.H2("🔥 AI Trading Dashboard"),
    dbc.Alert("Waiting...", id="status"),
    html.H3(id="ltp"),
    dcc.Graph(id="chart"),
    dash_table.DataTable(
        id="table",
        columns=[
            {"name": "Strike", "id": "Strike"},
            {"name": "CE LTP", "id": "CE LTP"},
            {"name": "PE LTP", "id": "PE LTP"},
        ],
        page_size=20
    ),
    dcc.Store(id="history-store", data=[]),
    dcc.Interval(id="ltp-interval", interval=LTP_INTERVAL_MS),
    dcc.Interval(id="oc-interval", interval=OC_INTERVAL_MS),
], fluid=True)

# ---------- CALLBACK 1 ----------
@app.callback(
    Output("ltp", "children"),
    Output("status", "children"),
    Output("status", "color"),
    Output("chart", "figure"),
    Output("history-store", "data"),
    Input("ltp-interval", "n_intervals"),
    State("history-store", "data"),
)
def update_ltp(_, history):
    history = history or []

    ltp, err = fetch_ltp()

    if err:
        return "ERROR", err, "warning", build_chart(history), history

    history.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "price": ltp
    })

    history = history[-MAX_POINTS:]

    return f"{ltp:.2f}", "LIVE", "success", build_chart(history), history

# ---------- CALLBACK 2 ----------
@app.callback(
    Output("table", "data"),
    Output("status", "children", allow_duplicate=True),
    Output("status", "color", allow_duplicate=True),
    Input("oc-interval", "n_intervals"),
    prevent_initial_call=True
)
def update_option_chain(_):
    rows, err = fetch_option_chain()

    if err:
        return [], err, "warning"

    return rows, "LIVE", "success"

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
