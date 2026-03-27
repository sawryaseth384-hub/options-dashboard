import os
import time
from datetime import datetime
import requests
import pandas as pd
import plotly.graph_objs as go
from dash import Dash, html, dcc, dash_table, Input, Output, State, no_update
import dash_bootstrap_components as dbc

# ---------------- ENV ----------------
CLIENT_ID = os.getenv("CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
PORT = int(os.environ.get("PORT", 5000))

headers = {
    "access-token": DHAN_ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
}

# ---------------- CONFIG ----------------
LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
EXPIRY_URL = "https://api.dhan.co/v2/optionChain/expiryList"
OPTION_CHAIN_URL = "https://api.dhan.co/v2/optionChain"

UNDERLYINGS = {"NIFTY": {"id": 13, "segment": "IDX_I"}}

MAX_POINTS = 150
REFRESH_MS = 1500
OPTION_REFRESH_EVERY = 12

session = requests.Session()

expiry_cache = {}
option_cache = {}

# ---------------- API ----------------
def post_api(url, payload):
    try:
        res = session.post(url, json=payload, headers=headers, timeout=3)
        if res.status_code == 401:
            return None, "Token expired"
        return res.json(), None
    except Exception as e:
        return None, str(e)

def fetch_ltp():
    data, err = post_api(LTP_URL, {"NSE_INDEX": [13]})
    if err:
        return None, err
    try:
        return float(data["data"][0]["ltp"]), None
    except:
        return None, "LTP error"

def fetch_expiry():
    now = time.time()
    if "NIFTY" in expiry_cache and now - expiry_cache["NIFTY"]["ts"] < 300:
        return expiry_cache["NIFTY"]["code"], None

    data, err = post_api(EXPIRY_URL, {"UnderlyingScrip": 13, "UnderlyingSeg": "IDX_I"})
    if err:
        return None, err

    code = data["data"][0]["expiryCode"]
    expiry_cache["NIFTY"] = {"code": code, "ts": now}
    return code, None

def fetch_option_chain(expiry):
    now = time.time()

    cached = option_cache.get("NIFTY")
    if cached and now - cached["ts"] < 10:
        return cached["rows"], None

    data, err = post_api(OPTION_CHAIN_URL, {
        "UnderlyingScrip": 13,
        "UnderlyingSeg": "IDX_I",
        "ExpiryCode": expiry
    })

    if err:
        return None, err

    rows = []
    for item in data.get("data", []):
        rows.append({
            "Strike": item.get("strikePrice"),
            "CE LTP": item.get("CE", {}).get("ltp"),
            "PE LTP": item.get("PE", {}).get("ltp")
        })

    option_cache["NIFTY"] = {"rows": rows, "ts": now}
    return rows, None

# ---------------- GRAPH ----------------
def build_chart(history):
    if not history:
        return go.Figure()

    df = pd.DataFrame(history)

    return go.Figure(
        data=[go.Scatter(x=df["time"], y=df["ltp"], mode="lines")],
        layout=go.Layout(template="plotly_dark")
    )

# ---------------- APP ----------------
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

app.layout = dbc.Container([
    dcc.Store(id="price-store", data=[]),
    dcc.Store(id="option-store", data=[]),

    html.H3("🔥 Stable Trading Dashboard"),

    dbc.Alert(id="status", children="Starting...", color="secondary"),

    html.H2(id="ltp"),

    dcc.Graph(id="chart"),

    dash_table.DataTable(
        id="table",
        columns=[
            {"name": "Strike", "id": "Strike"},
            {"name": "CE", "id": "CE LTP"},
            {"name": "PE", "id": "PE LTP"},
        ],
        page_size=15
    ),

    dcc.Interval(id="interval", interval=REFRESH_MS)
])

# ---------------- CALLBACK ----------------
@app.callback(
    [
        Output("price-store", "data"),
        Output("option-store", "data"),
        Output("ltp", "children"),
        Output("status", "children"),
        Output("chart", "figure"),
        Output("table", "data"),
    ],
    [Input("interval", "n_intervals")],
    [State("price-store", "data"), State("option-store", "data")]
)
def update(n, history, option_rows):
    history = history or []
    option_rows = option_rows or []

    # LTP
    ltp, err = fetch_ltp()
    if err:
        return history, option_rows, "--", err, build_chart(history), option_rows

    history.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "ltp": ltp
    })
    history = history[-MAX_POINTS:]

    status = "LIVE"

    # OPTION CHAIN (throttled)
    if n % OPTION_REFRESH_EVERY == 0:
        expiry, err = fetch_expiry()
        if not err:
            option_rows, _ = fetch_option_chain(expiry)

    return history, option_rows, f"{ltp:.2f}", status, build_chart(history), option_rows

# ---------------- RUN ----------------
if __name__ == "__main__":
    print(f"Running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
