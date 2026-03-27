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

PORT = int(os.environ.get("PORT", 3000))

HEADERS = {
    "access-token": DHAN_ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
}

# ---------- API ----------
LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"

# ---------- APP ----------
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

app.layout = dbc.Container(
    [
        html.H2("🔥 AI Trading Dashboard"),
        html.H3(id="ltp"),
        dcc.Interval(id="interval", interval=2000, n_intervals=0),
    ]
)

# ---------- FUNCTION ----------
def fetch_ltp():
    try:
        payload = {"NSE_INDEX": [13]}
        r = requests.post(LTP_URL, headers=HEADERS, json=payload, timeout=3)
        r.raise_for_status()
        return float(r.json()["data"][0]["lastPrice"])
    except:
        return None

# ---------- CALLBACK ----------
@app.callback(
    Output("ltp", "children"),
    Input("interval", "n_intervals")
)
def update_ltp(n):
    ltp = fetch_ltp()
    if ltp:
        return f"NIFTY: {ltp}"
    return "Error fetching data"

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False
    )
