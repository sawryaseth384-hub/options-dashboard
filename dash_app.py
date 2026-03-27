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
PORT = int(os.environ.get("PORT", 3000))  # Replit-provided port (fallback 3000)

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
LTP_INTERVAL_MS = 1000            # 1s LTP
OC_INTERVAL_MS = 8000             # 8s option chain
REQUEST_TIMEOUT = 3
MAX_POINTS = 150
OC_CACHE_TTL = 15                 # seconds
EXPIRY_CACHE_TTL = 300            # seconds
BACKOFF_CAP_MS = 30000            # 30s max backoff

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
        return None, f"LTP error: {type(e).__name__}: {e}"

def fetch_expiry():
    now = time.time()
    if expiry_cache["code"] and now - expiry_cache["time"] < EXPIRY_CACHE_TTL:
        return expiry_cache["code"], None
    try:
        r = requests.post(
            EXPIRY_URL,
            headers=HEADERS,
            json={"UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"], "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"]},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        code = r.json()["data"][0]["expiryCode"]
        expiry_cache["code"] = code
        expiry_cache["time"] = now
        return code, None
    except Exception as e:
        return None, f"Expiry error: {type(e).__name__}: {e}"

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
        return None, f"OC error: {type(e).__name__}: {e}"

def build_chart(history):
    if not history:
        return go.Figure(layout=go.Layout(template="plotly_dark", title="Live LTP"))
    df = pd.DataFrame(history)
    return go.Figure(
        data=[go.Scatter(x=df["time"], y=df["price"], mode="lines")],
        layout=go.Layout(template="plotly_dark", title="Live LTP"),
    )

def next_interval(prev_ms, failed):
    if not failed:
        return LTP_INTERVAL_MS
    return min(prev_ms * 2, BACKOFF_CAP_MS)

# ---------- APP ----------
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server  # required for compatibility

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
            style_cell={"backgroundColor": "#222", "color": "white"},
        ),
        dcc.Store(id="history-store", data=[]),
        dcc.Interval(id="ltp-interval", interval=LTP_INTERVAL_MS, n_intervals=0),
        dcc.Interval(id="oc-interval", interval=OC_INTERVAL_MS, n_intervals=0),
    ],
    fluid=True,
)

# ---------- CALLBACKS ----------
@app.callback(
    Output("ltp", "children"),
    Output("status", "children"),
    Output("status", "color"),
    Output("chart", "figure"),
    Output("history-store", "data"),
    Output("ltp-interval", "interval"),
    Input("ltp-interval", "n_intervals"),
    State("history-store", "data"),
    State("ltp-interval", "interval"),
    prevent_initial_call=False,
)
def update_ltp(_n, history, current_interval):
    history = history or []
    ltp, err = fetch_ltp()

    if err:
        new_interval = next_interval(current_interval, failed=True)
        return "ERROR", err, "warning", build_chart(history), history, new_interval

    timestamp = datetime.now().strftime("%H:%M:%S")
    history.append({"time": timestamp, "price": ltp})
    history = history[-MAX_POINTS:]

    return f"{ltp:.2f}", "LIVE", "success", build_chart(history), history, LTP_INTERVAL_MS

@app.callback(
    Output("table", "data"),
    Output("status", "children", allow_duplicate=True),
    Output("status", "color", allow_duplicate=True),
    Output("oc-interval", "interval"),
    Input("oc-interval", "n_intervals"),
    State("oc-interval", "interval"),
    prevent_initial_call=False,
)
def update_option_chain(_n, current_interval):
    rows, err = fetch_option_chain()
    if err:
        new_int = next_interval(current_interval, failed=True)
        return no_update, err, "warning", new_int
    return rows, "LIVE", "success", OC_INTERVAL_MS

# ---------- RUN ----------
if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 3000))  # CRITICAL: Replit port only
    print(f"Running on port {PORT}")
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,  # single process to avoid artifact crash
    )
