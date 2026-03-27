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
PORT = int(os.environ.get("PORT", 3000))  # Replit-provided port (fallback 3000)

headers = {
    "access-token": DHAN_ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
}

# ---------- API ----------
LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
OPTION_CHAIN_URL = "https://api.dhan.co/v2/optionChain"
EXPIRY_URL = "https://api.dhan.co/v2/optionChain/expiryList"

UNDERLYINGS = {"NIFTY": {"id": 13, "segment": "IDX_I"}}

# ---------- SETTINGS ----------
REFRESH_MS = 1000
OPTION_REFRESH_EVERY = 10
REQUEST_TIMEOUT = 3

# ---------- CACHE ----------
option_cache = {"data": [], "time": 0}

# ---------- FUNCTIONS ----------
def fetch_ltp():
    try:
        payload = {"NSE_INDEX": [UNDERLYINGS["NIFTY"]["id"]]}
        r = requests.post(LTP_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        return float(data["data"][0]["lastPrice"]), None
    except Exception as e:
        return None, str(e)

def fetch_option_chain():
    now = time.time()

    if now - option_cache["time"] < OPTION_REFRESH_EVERY:
        return option_cache["data"], None

    try:
        expiry = requests.post(
            EXPIRY_URL,
            headers=headers,
            json={"UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"], "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"]},
            timeout=REQUEST_TIMEOUT,
        ).json()

        expiry_code = expiry["data"][0]["expiryCode"]

        oc = requests.post(
            OPTION_CHAIN_URL,
            headers=headers,
            json={
                "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
                "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
                "ExpiryCode": expiry_code,
            },
            timeout=REQUEST_TIMEOUT,
        ).json()

        rows = []
        for item in oc["data"]:
            rows.append(
                {
                    "Strike": item["strikePrice"],
                    "CE LTP": item.get("CE", {}).get("lastPrice"),
                    "PE LTP": item.get("PE", {}).get("lastPrice"),
                }
            )

        option_cache["data"] = rows
        option_cache["time"] = now

        return rows, None

    except Exception as e:
        return None, str(e)

def build_chart(history):
    if not history:
        return go.Figure()

    df = pd.DataFrame(history)

    return go.Figure(
        data=[go.Scatter(x=df["time"], y=df["price"], mode="lines")],
        layout=go.Layout(template="plotly_dark", title="LTP"),
    )

# ---------- APP ----------
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server  # required for compatibility

app.layout = dbc.Container(
    [
        html.H2("🔥 AI Trading Dashboard"),
        dbc.Alert("Waiting...", id="status"),
        dbc.Row([dbc.Col(html.H3(id="ltp"))]),
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
        dcc.Interval(id="interval", interval=REFRESH_MS),
    ],
    fluid=True,
)

# ---------- CALLBACK ----------
@app.callback(
    Output("ltp", "children"),
    Output("status", "children"),
    Output("chart", "figure"),
    Output("table", "data"),
    Input("interval", "n_intervals"),
    State("chart", "figure"),
)
def update(n, fig):
    history = fig["data"][0]["y"] if fig and "data" in fig and fig["data"] else []

    ltp, err1 = fetch_ltp()
    oc, err2 = fetch_option_chain()

    if err1:
        return "Error", err1, build_chart([]), []

    history = history[-50:] + [ltp]
    chart_data = [{"time": datetime.now().strftime("%H:%M:%S"), "price": p} for p in history]

    return (
        f"{ltp:.2f}",
        "LIVE" if not err2 else err2,
        build_chart(chart_data),
        oc if oc else [],
    )

# ---------- RUN ----------
if __name__ == "__main__":
    print(f"Running on port {PORT}")
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
    )
