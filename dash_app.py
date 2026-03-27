import os, time
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
LTP_INTERVAL_MS = 1000           # 1s
OC_INTERVAL_MS = 8000            # 6–10s sweet spot
REQUEST_TIMEOUT = 3
OC_CACHE_TTL = 15                # seconds
BACKOFF_MAX_MS = 30000           # cap backoff at 30s

# ---------- CACHE ----------
option_cache = {"data": [], "expires": 0}

# ---------- HELPERS ----------
def fetch_ltp():
    payload = {"NSE_INDEX": [UNDERLYINGS["NIFTY"]["id"]]}
    r = requests.post(LTP_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return float(data["data"][0]["lastPrice"])

def fetch_option_chain():
    now = time.time()
    if now < option_cache["expires"] and option_cache["data"]:
        return option_cache["data"], option_cache.get("expiry_label", "-")

    # expiry
    exp_resp = requests.post(
        EXPIRY_URL,
        headers=headers,
        json={"UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"], "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"]},
        timeout=REQUEST_TIMEOUT,
    )
    exp_resp.raise_for_status()
    expiry = exp_resp.json()["data"][0]
    expiry_code = expiry["expiryCode"]
    expiry_label = expiry.get("displayName") or expiry.get("expiryDate") or str(expiry_code)

    # option chain
    oc_resp = requests.post(
        OPTION_CHAIN_URL,
        headers=headers,
        json={
            "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
            "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
            "ExpiryCode": expiry_code,
        },
        timeout=REQUEST_TIMEOUT,
    )
    oc_resp.raise_for_status()
    oc = oc_resp.json()

    rows = [
        {
            "Strike": item["strikePrice"],
            "CE LTP": item.get("CE", {}).get("lastPrice"),
            "PE LTP": item.get("PE", {}).get("lastPrice"),
        }
        for item in oc["data"]
    ]

    option_cache["data"] = rows
    option_cache["expires"] = now + OC_CACHE_TTL
    option_cache["expiry_label"] = expiry_label
    return rows, expiry_label

def build_chart(history):
    if not history:
        return go.Figure(layout=go.Layout(template="plotly_dark", title="LTP"))
    df = pd.DataFrame(history)
    return go.Figure(
        data=[go.Scatter(x=df["time"], y=df["price"], mode="lines+markers")],
        layout=go.Layout(template="plotly_dark", title="LTP")
    )

def next_interval(prev_ms, failed):
    if not failed:
        return LTP_INTERVAL_MS
    return min(prev_ms * 2, BACKOFF_MAX_MS)

# ---------- APP ----------
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

app.layout = dbc.Container(
    [
        html.H2("🔥 AI Trading Dashboard"),
        dbc.Alert("Waiting...", id="status", color="secondary"),
        dbc.Row([dbc.Col(html.H3(id="ltp"))]),
        html.Div(id="meta", style={"color": "#ccc", "marginBottom": "8px"}),
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
        dcc.Store(id="hist-store", data=[]),
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
    Output("hist-store", "data"),
    Output("chart", "figure"),
    Output("ltp-interval", "interval"),
    Input("ltp-interval", "n_intervals"),
    State("hist-store", "data"),
    State("ltp-interval", "interval"),
    prevent_initial_call=False,
)
def update_ltp(_n, history, current_interval):
    history = history or []
    try:
        price = fetch_ltp()
        history = (history + [{"time": datetime.now().strftime("%H:%M:%S"), "price": price}])[-120:]
        fig = build_chart(history)
        return (
            f"{price:.2f}",
            "LIVE",
            "success",
            history,
            fig,
            LTP_INTERVAL_MS,
        )
    except Exception as e:
        # backoff and keep previous history/figure
        new_int = next_interval(current_interval, failed=True)
        return (
            "ERROR",
            f"BACKOFF: {type(e).__name__}: {e}",
            "warning",
            history,
            build_chart(history),
            new_int,
        )

@app.callback(
    Output("table", "data"),
    Output("meta", "children"),
    Output("status", "children", allow_duplicate=True),
    Output("status", "color", allow_duplicate=True),
    Output("oc-interval", "interval"),
    Input("oc-interval", "n_intervals"),
    State("oc-interval", "interval"),
    prevent_initial_call=False,
)
def update_option_chain(_n, current_interval):
    try:
        rows, expiry_label = fetch_option_chain()
        meta = f"Expiry: {expiry_label} | Rows: {len(rows)}"
        return rows, meta, no_update, no_update, OC_INTERVAL_MS
    except Exception as e:
        new_int = next_interval(current_interval, failed=True)
        return no_update, no_update, f"OC BACKOFF: {type(e).__name__}: {e}", "warning", new_int

# ---------- RUN ----------
if __name__ == "__main__":
    print(f"Running on port {PORT}")
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,  # single process; prevents artifact crash
    )
