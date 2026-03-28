import os
import time
import json
from datetime import datetime
import requests
import pandas as pd
import plotly.graph_objs as go
from dash import Dash, html, dcc, dash_table, Input, Output, State, no_update
import dash_bootstrap_components as dbc

# ---------- ENV ----------
CLIENT_ID = os.getenv("CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
PORT = int(os.environ.get("PORT", 8080))  # Railway provides PORT; fallback 8080

_missing = [name for name, val in [("CLIENT_ID", CLIENT_ID), ("DHAN_ACCESS_TOKEN", DHAN_ACCESS_TOKEN)] if not val]
if _missing:
    raise EnvironmentError(f"Required environment variable(s) not set: {', '.join(_missing)}")

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
LTP_INTERVAL_MS = 1000            # 1s LTP polling
OC_INTERVAL_MS = 8000             # 8s option chain polling
try:
    REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", 3))
except ValueError:
    raise ValueError("REQUEST_TIMEOUT environment variable must be a numeric value (e.g. 3 or 3.5)")
MAX_POINTS = 150
OC_CACHE_TTL = 15                 # seconds
EXPIRY_CACHE_TTL = 300            # seconds
BACKOFF_CAP_MS = 30000            # 30s max backoff

# ---------- CACHE ----------
option_cache: dict = {"data": [], "time": 0}
expiry_cache: dict = {"code": None, "time": 0}
FALLBACK_ROWS = [{"Strike": "-", "CE LTP": "-", "PE LTP": "-"} for _ in range(10)]

# ---------- HELPERS ----------
def fetch_ltp():
    try:
        payload = {"NSE_INDEX": [UNDERLYINGS["NIFTY"]["id"]]}
        r = requests.post(LTP_URL, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json().get("data", {})
        price = None
        if isinstance(data, list) and data:
            price = data[0].get("ltp") or data[0].get("lastPrice")
        elif isinstance(data, dict) and data:
            first_seg = next(iter(data.values()), {})
            if isinstance(first_seg, list) and first_seg:
                price = first_seg[0].get("ltp") or first_seg[0].get("lastPrice")
            elif isinstance(first_seg, dict):
                price = first_seg.get("ltp") or first_seg.get("lastPrice")
        if price is None:
            return None, "LTP error: empty data"
        return float(price), None
    except Exception as e:
        return None, f"LTP error: {type(e).__name__}: {e}"


def fetch_expiry():
    now = time.time()
    if expiry_cache["code"] and now - expiry_cache["time"] < EXPIRY_CACHE_TTL:
        return expiry_cache["code"], None
    try:
        payload = {
            "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
            "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
        }
        r = requests.post(EXPIRY_URL, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json().get("data") or []
        if not data:
            return None, "Expiry error: empty data"
        first = data[0]
        code = first.get("expiryCode") if isinstance(first, dict) else first
        expiry_cache["code"] = code
        expiry_cache["time"] = now
        return code, None
    except Exception as e:
        return None, f"Expiry error: {type(e).__name__}: {e}"


def _extract_price(side_dict: dict):
    """Safely extract price from CE/PE dict."""
    if not side_dict:
        return None
    return (
        side_dict.get("ltp")
        or side_dict.get("lastPrice")
        or side_dict.get("LTP")
        or side_dict.get("price")
    )


def fetch_option_chain():
    now = time.time()
    if option_cache["data"] and now - option_cache["time"] < OC_CACHE_TTL:
        return option_cache["data"], None

    expiry_code, err = fetch_expiry()
    if err:
        return FALLBACK_ROWS, err

    try:
        payload = {
            "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
            "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
            "ExpiryCode": expiry_code,
        }
        r = requests.post(OPTION_CHAIN_URL, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json().get("data")
        if not data:
            return FALLBACK_ROWS, "OC warning: empty data"

        rows = [
            {
                "Strike": item.get("strikePrice"),
                "CE LTP": _extract_price(item.get("CE", {})),
                "PE LTP": _extract_price(item.get("PE", {})),
            }
            for item in data
        ]

        option_cache["data"] = rows
        option_cache["time"] = now
        return rows, None
    except Exception as e:
        return FALLBACK_ROWS, f"OC error: {type(e).__name__}: {e}"


def build_chart(history):
    if not history:
        return go.Figure(layout=go.Layout(template="plotly_dark", title="Live NIFTY LTP"))
    df = pd.DataFrame(history)
    return go.Figure(
        data=[go.Scatter(x=df["time"], y=df["price"], mode="lines", line={"color": "#00d4aa"})],
        layout=go.Layout(
            template="plotly_dark",
            title="Live NIFTY LTP",
            xaxis_title="Time",
            yaxis_title="Price",
            margin={"l": 40, "r": 20, "t": 40, "b": 40},
        ),
    )


def next_interval(prev_ms, failed):
    if not failed:
        return LTP_INTERVAL_MS
    return min(prev_ms * 2, BACKOFF_CAP_MS)


# ---------- APP ----------
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    title="AI Trading Dashboard",
)
server = app.server  # WSGI entry point for gunicorn / Railway

app.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                html.H2("🔥 AI Trading Dashboard", className="text-center mt-3 mb-2"),
            )
        ),
        dbc.Row(
            dbc.Col(
                dbc.Alert("Waiting...", id="status", color="secondary", className="text-center"),
            )
        ),
        dbc.Row(
            dbc.Col(
                html.H3(id="ltp", className="text-center text-info mb-3"),
            )
        ),
        dbc.Row(
            dbc.Col(
                dcc.Loading(
                    id="chart-loading",
                    type="default",
                    children=dcc.Graph(id="chart"),
                ),
            )
        ),
        dbc.Row(
            dbc.Col(
                dcc.Loading(
                    id="table-loading",
                    type="default",
                    children=dash_table.DataTable(
                        id="table",
                        columns=[
                            {"name": "Strike", "id": "Strike"},
                            {"name": "CE LTP", "id": "CE LTP"},
                            {"name": "PE LTP", "id": "PE LTP"},
                        ],
                        page_size=20,
                        style_header={
                            "backgroundColor": "#1a1a2e",
                            "color": "#00d4aa",
                            "fontWeight": "bold",
                        },
                        style_cell={
                            "backgroundColor": "#16213e",
                            "color": "#e0e0e0",
                            "border": "1px solid #0f3460",
                            "textAlign": "center",
                        },
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": "#1a1a2e",
                            }
                        ],
                    ),
                ),
                className="mt-3",
            )
        ),
        dcc.Store(id="history-store", data=[]),
        dcc.Interval(id="ltp-interval", interval=LTP_INTERVAL_MS, n_intervals=0),
        dcc.Interval(id="oc-interval", interval=OC_INTERVAL_MS, n_intervals=0),
    ],
    fluid=True,
    style={"backgroundColor": "#0d1117", "minHeight": "100vh"},
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

    return f"NIFTY: {ltp:.2f}", "LIVE", "success", build_chart(history), history, LTP_INTERVAL_MS


@app.callback(
    Output("table", "data"),
    Output("status", "children", allow_duplicate=True),
    Output("status", "color", allow_duplicate=True),
    Output("oc-interval", "interval"),
    Input("oc-interval", "n_intervals"),
    State("oc-interval", "interval"),
    prevent_initial_call="initial_duplicate",
)
def update_option_chain(_n, current_interval):
    rows, err = fetch_option_chain()
    if err:
        new_interval = next_interval(current_interval, failed=True)
        return rows, err, "warning", new_interval
    return rows, "LIVE", "success", OC_INTERVAL_MS


# ---------- RUN ----------
if __name__ == "__main__":
    print(f"Starting production server on port {PORT}")
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
    )
