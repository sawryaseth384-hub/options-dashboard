import os
import time
from datetime import datetime
import requests
import pandas as pd
import plotly.graph_objs as go
from dash import Dash, html, dcc, dash_table, Input, Output, State, no_update
import dash_bootstrap_components as dbc

# ---------- ENV ----------
CLIENT_ID = os.getenv("CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

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
OC_CACHE_TTL = 15
EXPIRY_CACHE_TTL = 300
BACKOFF_CAP_MS = 30000

# ---------- CACHE ----------
option_cache = {"data": [], "time": 0}
expiry_cache = {"code": None, "time": 0}

# ---------- HELPERS ----------
def fetch_ltp():
    try:
        payload = {"NSE_INDEX": [UNDERLYINGS["NIFTY"]["id"]]}
        r = requests.post(LTP_URL, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        return float(data["data"][0]["lastPrice"]), None
    except Exception as e:
        return None, str(e)

def fetch_expiry():
    now = time.time()
    if expiry_cache["code"] and now - expiry_cache["time"] < EXPIRY_CACHE_TTL:
        return expiry_cache["code"], None
    try:
        r = requests.post(
            EXPIRY_URL,
            headers=HEADERS,
            json={
                "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
                "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
            },
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        code = r.json()["data"][0]["expiryCode"]
        expiry_cache["code"] = code
        expiry_cache["time"] = now
        return code, None
    except Exception as e:
        return None, str(e)

def fetch_option_chain():
    now = time.time()
    if option_cache["data"] and now - option_cache["time"] < OC_CACHE_TTL:
        return option_cache["data"], None

    expiry_code, err = fetch_expiry()
    if err:
        return None, err

    try:
        r = requests.post(
            OPTION_CHAIN_URL,
            headers=HEADERS,
            json={
                "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
                "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
                "ExpiryCode": expiry_code,
            },
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        rows = [
            {
                "Strike": item["strikePrice"],
                "CE LTP": item.get("CE", {}).get("lastPrice"),
                "PE LTP": item.get("PE", {}).get("lastPrice"),
            }
            for item in r.json()["data"]
        ]
        option_cache["data"] = rows
        option_cache["time"] = now
        return rows, None
    except Exception as e:
        return None, str(e)

def build_chart(history):
    if not history:
        return go.Figure(layout=go.Layout(template="plotly_dark", title="Waiting..."))

    df = pd.DataFrame(history)
    fig = go.Figure(
        data=[go.Scatter(x=df["time"], y=df["price"], mode="lines+markers")]
    )
    fig.update_layout(template="plotly_dark", title="Live LTP")
    return fig

def next_interval(prev, failed):
    return min(prev * 2, BACKOFF_CAP_MS) if failed else LTP_INTERVAL_MS

# ---------- APP ----------
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

app.layout = dbc.Container(
    [
        html.H2("🔥 Trading Dashboard"),
        dbc.Alert("Starting...", id="status"),
        html.H3(id="ltp"),
        dcc.Graph(id="chart"),
        dash_table.DataTable(
            id="table",
            columns=[
                {"name": "Strike", "id": "Strike"},
                {"name": "CE", "id": "CE LTP"},
                {"name": "PE", "id": "PE LTP"},
            ],
            page_size=20,
        ),
        dcc.Store(id="history", data=[]),
        dcc.Interval(id="ltp-int", interval=LTP_INTERVAL_MS),
        dcc.Interval(id="oc-int", interval=OC_INTERVAL_MS),
    ],
)

# ---------- CALLBACKS ----------
@app.callback(
    Output("ltp", "children"),
    Output("status", "children"),
    Output("chart", "figure"),
    Output("history", "data"),
    Input("ltp-int", "n_intervals"),
    State("history", "data"),
)
def update_ltp(n, history):
    history = history or []
    ltp, err = fetch_ltp()

    if err:
        return "ERROR", err, build_chart(history), history

    now = datetime.now().strftime("%H:%M:%S")
    history.append({"time": now, "price": ltp})
    history = history[-MAX_POINTS:]

    return f"{ltp}", "LIVE", build_chart(history), history

@app.callback(
    Output("table", "data"),
    Input("oc-int", "n_intervals"),
)
def update_oc(n):
    rows, _ = fetch_option_chain()
    return rows or []

# ---------- RUN ----------
if __
