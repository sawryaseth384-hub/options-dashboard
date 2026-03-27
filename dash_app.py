import os
import json
from datetime import datetime
import requests
import pandas as pd
import plotly.graph_objs as go
from dash import Dash, html, dcc, dash_table, Input, Output, State, no_update
import dash_bootstrap_components as dbc

# ---------- Environment ----------
CLIENT_ID = os.getenv("CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

headers = {
    "access-token": DHAN_ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json"
}

# ---------- Constants ----------
LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
EXPIRY_URL = "https://api.dhan.co/v2/optionChain/expiryList"
OPTION_CHAIN_URL = "https://api.dhan.co/v2/optionChain"
UNDERLYINGS = {
    "NIFTY": {"id": 13, "segment": "IDX_I"}  # Extend here if you add more symbols
}
MAX_POINTS = 100
REQUEST_TIMEOUT = 5

# ---------- Helpers ----------
def mask_token(token: str) -> str:
    if not token:
        return "MISSING"
    if len(token) <= 6:
        return token[0] + "***"
    return token[:4] + "***" + token[-2:]

def log_debug(url, payload, response=None, error=None):
    status = response.status_code if response else "NO_RESPONSE"
    body_preview = ""
    if response:
        try:
            body_preview = response.text[:300]
        except Exception:
            body_preview = "<unreadable>"
    if error:
        body_preview = f"ERROR: {error}"
    print("\n--- DHAN DEBUG ---")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload)}")
    print(f"Status Code: {status}")
    print(f"Response (first 300 chars): {body_preview}")
    print("------------------\n")

def post_api(url, payload):
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        log_debug(url, payload, response=resp)
    except Exception as e:
        log_debug(url, payload, response=None, error=str(e))
        return None, f"Request error: {e}"

    if resp.status_code == 401:
        return None, "Token invalid or expired"

    try:
        data = resp.json()
    except ValueError:
        return None, f"Non-JSON response: {resp.text[:200]}"
    return data, None

def fetch_ltp(underlying_id: int):
    payload = {"NSE_INDEX": [underlying_id]}
    data, err = post_api(LTP_URL, payload)
    if err:
        return None, err
    # Try to extract LTP robustly
    ltp = None
    try:
        items = data.get("data") or data.get("ltp") or data
        if isinstance(items, list) and items:
            candidate = items[0]
            ltp = (
                candidate.get("ltp")
                or candidate.get("LTP")
                or candidate.get("lastPrice")
                or candidate.get("LastPrice")
            )
        elif isinstance(items, dict):
            ltp = (
                items.get("ltp")
                or items.get("LTP")
                or items.get("lastPrice")
                or items.get("LastPrice")
            )
    except Exception:
        pass

    if ltp is None:
        return None, "LTP data missing in response"
    return float(ltp), None

def fetch_expiry_code(underlying_id: int, segment: str):
    payload = {"UnderlyingScrip": underlying_id, "UnderlyingSeg": segment}
    data, err = post_api(EXPIRY_URL, payload)
    if err:
        return None, err
    expiry_list = (
        data.get("data")
        or data.get("expiryList")
        or data.get("expiries")
        or data
    )
    code = None
    if isinstance(expiry_list, list) and expiry_list:
        first = expiry_list[0]
        if isinstance(first, dict):
            code = first.get("expiryCode") or first.get("ExpiryCode") or first.get("code") or first.get("Code")
        elif isinstance(first, (str, int)):
            code = first
    if code is None:
        return None, "Expiry code missing in response"
    return code, None

def parse_option_chain(json_data):
    rows = []
    options = json_data.get("data") or json_data.get("options") or json_data.get("optionChain") or []
    if not isinstance(options, list):
        return rows
    for item in options:
        strike = item.get("strikePrice") or item.get("StrikePrice") or item.get("strike")
        ce = pe = None
        if isinstance(item.get("callOption"), dict):
            ce = item["callOption"].get("ltp") or item["callOption"].get("LTP")
        if isinstance(item.get("putOption"), dict):
            pe = item["putOption"].get("ltp") or item["putOption"].get("LTP")
        if isinstance(item.get("CE"), dict):
            ce = ce or item["CE"].get("ltp") or item["CE"].get("LTP")
        if isinstance(item.get("PE"), dict):
            pe = pe or item["PE"].get("ltp") or item["PE"].get("LTP")
        if strike is not None:
            rows.append({"Strike": strike, "CE LTP": ce, "PE LTP": pe})
    return rows

def fetch_option_chain(underlying_id: int, segment: str, expiry_code):
    payload = {
        "UnderlyingScrip": underlying_id,
        "UnderlyingSeg": segment,
        "ExpiryCode": expiry_code,
    }
    data, err = post_api(OPTION_CHAIN_URL, payload)
    if err:
        return [], err
    rows = parse_option_chain(data)
    if not rows:
        return [], "Option chain data missing in response"
    return rows, None

def build_price_figure(history):
    if not history:
        return go.Figure(
            layout=go.Layout(
                template="plotly_dark",
                title="Price History (waiting for data)",
                xaxis_title="Time",
                yaxis_title="LTP",
            )
        )
    df = pd.DataFrame(history)
    fig = go.Figure(
        data=[go.Scatter(x=df["time"], y=df["ltp"], mode="lines+markers", name="LTP")],
        layout=go.Layout(
            template="plotly_dark",
            title="Live LTP (last 100 points)",
            xaxis_title="Time",
            yaxis_title="LTP",
        ),
    )
    return fig

# ---------- Dash App ----------
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

app.layout = dbc.Container(
    [
        dcc.Store(id="price-store", data=[]),
        html.H2("Dhan Trading Dashboard", className="my-3"),
        dbc.Alert(id="status-banner", color="secondary", className="mb-3"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Symbol"),
                        dcc.Dropdown(
                            id="symbol-dropdown",
                            options=[{"label": "NIFTY 50", "value": "NIFTY"}],
                            value="NIFTY",
                            clearable=False,
                        ),
                    ],
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Latest Traded Price"),
                                html.H2(id="ltp-card-value", children="--"),
                            ]
                        ),
                        className="mt-2",
                    ),
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(id="debug-panel"),
                        className="mt-2",
                    ),
                    md=6,
                ),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id="ltp-graph"), md=12),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    dash_table.DataTable(
                        id="option-chain-table",
                        columns=[
                            {"name": "Strike", "id": "Strike"},
                            {"name": "CE LTP", "id": "CE LTP"},
                            {"name": "PE LTP", "id": "PE LTP"},
                        ],
                        data=[],
                        style_table={"overflowX": "auto"},
                        style_header={"backgroundColor": "#1f1f1f", "color": "white"},
                        style_cell={"backgroundColor": "#2b2b2b", "color": "white"},
                        page_size=20,
                    ),
                    md=12,
                )
            ]
        ),
        dcc.Interval(id="update-interval", interval=5000, n_intervals=0),
    ],
    fluid=True,
)

# ---------- Callbacks ----------
@app.callback(
    [
        Output("price-store", "data"),
        Output("ltp-card-value", "children"),
        Output("status-banner", "children"),
        Output("status-banner", "color"),
        Output("ltp-graph", "figure"),
        Output("option-chain-table", "data"),
        Output("debug-panel", "children"),
    ],
    [Input("update-interval", "n_intervals"), Input("symbol-dropdown", "value")],
    [State("price-store", "data")],
)
def refresh_data(n, symbol, history):
    history = history or []
    status_msgs = []
    status_color = "secondary"

    # Env check
    if not CLIENT_ID or not DHAN_ACCESS_TOKEN:
        msg = "Missing CLIENT_ID or DHAN_ACCESS_TOKEN environment variables."
        return history, "--", msg, "danger", build_price_figure(history), [], build_debug_panel(msg)

    underlying = UNDERLYINGS.get(symbol)
    if not underlying:
        msg = f"Unsupported symbol: {symbol}"
        return history, "--", msg, "danger", build_price_figure(history), [], build_debug_panel(msg)

    # Fetch LTP
    ltp, err = fetch_ltp(underlying["id"])
    if err:
        status_msgs.append(f"LTP: {err}")
    else:
        timestamp = datetime.now().strftime("%H:%M:%S")
        history.append({"time": timestamp, "ltp": ltp})
        history = history[-MAX_POINTS:]
        status_msgs.append("LTP fetched")
        status_color = "success"

    # Fetch expiry
    expiry_code, expiry_err = fetch_expiry_code(underlying["id"], underlying["segment"])
    if expiry_err:
        status_msgs.append(f"Expiry: {expiry_err}")
        option_rows = []
    else:
        # Fetch option chain
        option_rows, oc_err = fetch_option_chain(underlying["id"], underlying["segment"], expiry_code)
        if oc_err:
            status_msgs.append(f"Option Chain: {oc_err}")
        else:
            status_msgs.append("Option Chain fetched")
            if status_color != "danger":
                status_color = "success"

    status_text = " | ".join(status_msgs) if status_msgs else "Idle"
    ltp_text = f"{ltp:.2f}" if ltp is not None else "--"

    debug_panel = build_debug_panel(
        status_text,
        last_ltp=ltp_text,
        expiry_code=expiry_code if not expiry_err else None,
        option_rows=len(option_rows),
    )

    return history, ltp_text, status_text, status_color, build_price_figure(history), option_rows, debug_panel

def build_debug_panel(status, last_ltp=None, expiry_code=None, option_rows=0):
    return html.Div(
        [
            html.Div(f"Status: {status}"),
            html.Div(f"CLIENT_ID: {mask_token(CLIENT_ID)}"),
            html.Div(f"ACCESS_TOKEN: {mask_token(DHAN_ACCESS_TOKEN)}"),
            html.Div(f"Last LTP: {last_ltp or '--'}"),
            html.Div(f"Expiry Code: {expiry_code or '--'}"),
            html.Div(f"Option Rows: {option_rows}"),
        ]
    )

# ---------- Entrypoint ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
