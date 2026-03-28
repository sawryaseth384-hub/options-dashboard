import os
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

HEADERS = {
    "access-token": DHAN_ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
}

print("APP STARTED")
print("CLIENT:", CLIENT_ID)
print("TOKEN:", "OK" if DHAN_ACCESS_TOKEN else "MISSING")

# ---------- API ----------
LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
EXPIRY_URL = "https://api.dhan.co/v2/optionChain/expiryList"
OPTION_CHAIN_URL = "https://api.dhan.co/v2/optionChain"

UNDERLYINGS = {"NIFTY": {"id": 13, "segment": "IDX_I"}}

# ---------- SETTINGS ----------
LTP_INTERVAL_MS = 1000
OC_INTERVAL_MS = 8000
REQUEST_TIMEOUT = 1  # seconds
MAX_POINTS = 150
MAX_OC_ROWS = 30
MAX_RETRIES = 1  # optional single retry for resilience

# ---------- HELPERS ----------
def _post_with_retry(url, payload):
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = requests.post(url, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.json(), None
        except Exception as e:
            last_err = e
            print(f"REQUEST ERROR ({url}) attempt {attempt+1}: {e}")
    return None, str(last_err)


def fetch_ltp():
    try:
        payload = {"NSE_INDEX": [UNDERLYINGS["NIFTY"]["id"]]}
        data, err = _post_with_retry(LTP_URL, payload)
        if err:
            return None, err

        data = data.get("data", {})
        if isinstance(data, list) and data:
            price = data[0].get("ltp") or data[0].get("lastPrice")
            if price:
                return float(price), None

        return None, "No LTP data"
    except Exception as e:
        print("LTP ERROR:", e)
        return None, str(e)


def fetch_expiry():
    try:
        payload = {
            "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
            "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
        }

        data, err = _post_with_retry(EXPIRY_URL, payload)
        if err:
            return None, err

        expiries = data.get("data", [])
        if not expiries:
            return None, "No expiry data"

        return expiries[0].get("expiryCode"), None
    except Exception as e:
        print("EXPIRY ERROR:", e)
        return None, str(e)


def fetch_option_chain():
    try:
        expiry, err = fetch_expiry()
        if err or not expiry:
            return [], err

        payload = {
            "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
            "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
            "ExpiryCode": expiry,
        }

        data, err = _post_with_retry(OPTION_CHAIN_URL, payload)
        if err:
            return [], err

        chain = data.get("data", [])
        rows = []
        for item in chain[:MAX_OC_ROWS]:
            rows.append(
                {
                    "Strike": item.get("strikePrice"),
                    "CE LTP": item.get("CE", {}).get("ltp"),
                    "PE LTP": item.get("PE", {}).get("ltp"),
                }
            )

        return rows, None
    except Exception as e:
        print("OC ERROR:", e)
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
        print("CHART ERROR:", e)
        return go.Figure()


# ---------- APP ----------
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True,
)

app.title = "Trading Dashboard"

# Expose Flask server for Gunicorn
server = app.server

# ---------- LAYOUT ----------
app.layout = dbc.Container(
    [
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
            page_size=20,
        ),
        dcc.Store(id="history-store", data=[]),
        dcc.Interval(id="ltp-interval", interval=LTP_INTERVAL_MS),
        dcc.Interval(id="oc-interval", interval=OC_INTERVAL_MS),
    ],
    fluid=True,
)

# ---------- CALLBACK 1 ----------
@app.callback(
    Output("ltp", "children"),
    Output("status", "children", allow_duplicate=True),
    Output("status", "color", allow_duplicate=True),
    Output("chart", "figure"),
    Output("history-store", "data"),
    Input("ltp-interval", "n_intervals"),
    State("history-store", "data"),
    prevent_initial_call="initial_duplicate",  # ✅ YE CHANGE KARNA HAI
)# ---------- CALLBACK 2 ----------
@app.callback(
    Output("table", "data"),
    Input("oc-interval", "n_intervals"),
    prevent_initial_call=True,
)
def update_option_chain(n):
    if n is None or n == 0:
        return []

    rows, err = fetch_option_chain()
    if err:
        return []

    return rows
    # ---------- IMPORTANT ----------
# No app.run(); Gunicorn serves via `server`
