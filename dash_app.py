import os
import time
import requests
import pandas as pd
import dash
from dash import dcc, html, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go

# ------------------
# ENV + CONSTANTS
# ------------------
CLIENT_ID = os.getenv("CLIENT_ID", "")
TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "")
BASE_URL = "https://api.dhan.co"
REFRESH_MS = 5000

SYMBOL_MAP = {
    "NIFTY": {"seg": "NSE_INDEX", "code": 13, "opt_seg": "IDX_I"},
    # token for RELIANCE on NSE cash; feel free to adjust if your mapping differs
    "RELIANCE": {"seg": "NSE_EQ", "code": 2885, "opt_seg": None},
}

HEADERS = {
    "access-token": TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
}

# ------------------
# HELPERS
# ------------------
def mask(value: str, show: int = 3) -> str:
    if not value:
        return "not set"
    return value[:show] + "*" * max(len(value) - show, 0)

def api_post(path: str, payload: dict):
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        return resp
    except Exception as exc:
        return {"error": str(exc)}

def get_ltp(symbol: str):
    meta = SYMBOL_MAP[symbol]
    payload = {meta["seg"]: [meta["code"]]}
    resp = api_post("/v2/marketfeed/ltp", payload)
    if isinstance(resp, dict):
        return None, "API error: " + resp["error"]
    if resp.status_code == 401:
        return None, "Token expired or invalid"
    if not resp.ok:
        return None, f"API failure: {resp.status_code} {resp.text}"
    data = resp.json()
    # expected structure: {"data":[{"ltp":...}]}
    try:
        ltp_val = data["data"][0]["ltp"]
        return float(ltp_val), "OK"
    except Exception:
        return None, f"Unexpected LTP payload: {data}"

def get_expiry_list():
    payload = {"UnderlyingScrip": 13, "UnderlyingSeg": "IDX_I"}
    resp = api_post("/v2/optionChain/expiryList", payload)
    if isinstance(resp, dict):
        return None, "API error: " + resp["error"]
    if resp.status_code == 401:
        return None, "Token expired or invalid"
    if not resp.ok:
        return None, f"API failure: {resp.status_code} {resp.text}"
    data = resp.json()
    expiries = data.get("data") or data.get("expiryList") or data
    if not expiries:
        return None, "Empty expiry list"
    first = expiries[0]
    # handle either code or string date
    expiry_code = first.get("expiryCode") or first.get("expirycode") or first.get("ExpiryCode") or first
    return expiry_code, "OK"

def get_option_chain():
    expiry_code, msg = get_expiry_list()
    if expiry_code is None:
        return None, msg
    payload = {"UnderlyingScrip": 13, "UnderlyingSeg": "IDX_I", "ExpiryCode": expiry_code}
    resp = api_post("/v2/optionChain", payload)
    if isinstance(resp, dict):
        return None, "API error: " + resp["error"]
    if resp.status_code == 401:
        return None, "Token expired or invalid"
    if not resp.ok:
        return None, f"API failure: {resp.status_code} {resp.text}"
    try:
        data = resp.json().get("data") or resp.json()
        # normalise rows
        rows = []
        for row in data:
            strike = row.get("strikePrice") or row.get("strikeprice") or row.get("strike") or 0
            ce = row.get("callLtp") or row.get("CE", {}).get("ltp") or row.get("call", {}).get("ltp")
            pe = row.get("putLtp") or row.get("PE", {}).get("ltp") or row.get("put", {}).get("ltp")
            rows.append({"Strike": strike, "CE LTP": ce, "PE LTP": pe})
        df = pd.DataFrame(rows).sort_values("Strike")
        return df.to_dict("records"), "OK"
    except Exception as exc:
        return None, f"Unexpected option-chain payload: {exc}"

# ------------------
# DASH APP
# ------------------
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    title="Dhan Trading Dashboard",
)
app.layout = dbc.Container(
    fluid=True,
    children=[
        dcc.Store(id="price-history", data=[]),
        html.Br(),
        dbc.Row(
            [
                dbc.Col(html.H2("Dhan Trading Dashboard"), md=8),
                dbc.Col(
                    dcc.Dropdown(
                        id="symbol-dropdown",
                        options=[{"label": k, "value": k} for k in SYMBOL_MAP],
                        value="NIFTY",
                        clearable=False,
                        style={"color": "#000"},
                    ),
                    md=4,
                ),
            ],
            align="center",
        ),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Last Traded Price"),
                            dbc.CardBody(html.H1(id="ltp-display", children="--")),
                        ],
                        color="dark",
                        outline=True,
                    ),
                    md=4,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Live Price Chart"),
                            dbc.CardBody(dcc.Graph(id="price-chart", config={"displayModeBar": False})),
                        ],
                        color="dark",
                        outline=True,
                    ),
                    md=8,
                ),
            ]
        ),
        html.Br(),
        dbc.Card(
            [
                dbc.CardHeader("Option Chain (Strike | CE LTP | PE LTP)"),
                dbc.CardBody(
                    dash_table.DataTable(
                        id="option-chain-table",
                        columns=[
                            {"name": "Strike", "id": "Strike"},
                            {"name": "CE LTP", "id": "CE LTP"},
                            {"name": "PE LTP", "id": "PE LTP"},
                        ],
                        data=[],
                        style_header={"backgroundColor": "#1f1f1f", "color": "white"},
                        style_cell={"backgroundColor": "#111", "color": "white"},
                        style_table={"height": "400px", "overflowY": "auto"},
                    )
                ),
            ],
            color="dark",
            outline=True,
        ),
        html.Br(),
        dbc.Alert(id="status-message", children="Waiting for first update...", color="secondary"),
        dbc.Card(
            [
                dbc.CardHeader("Debug Panel"),
                dbc.CardBody(
                    [
                        html.Div(f"CLIENT_ID: {mask(CLIENT_ID)}"),
                        html.Div(f"TOKEN: {mask(TOKEN)}"),
                        html.Div(id="debug-api-status", children="API status: --"),
                        html.Div(f"Refresh every: {REFRESH_MS/1000:.1f}s"),
                    ]
                ),
            ],
            color="secondary",
            outline=True,
        ),
        dcc.Interval(id="interval", interval=REFRESH_MS, n_intervals=0),
    ],
)

# ------------------
# CALLBACKS
# ------------------
@app.callback(
    [
        Output("ltp-display", "children"),
        Output("price-history", "data"),
        Output("option-chain-table", "data"),
        Output("status-message", "children"),
        Output("status-message", "color"),
        Output("debug-api-status", "children"),
    ],
    [Input("interval", "n_intervals"), Input("symbol-dropdown", "value")],
    [State("price-history", "data")],
)
def refresh_data(n, symbol, history):
    ts = time.strftime("%H:%M:%S")
    history = history or []

    ltp, ltp_status = get_ltp(symbol)
    status_color = "success" if ltp is not None else "danger"

    # append history only if valid
    if ltp is not None:
        history.append({"time": ts, "price": ltp})
        history = history[-120:]  # keep last 10 minutes at 5s cadence

    # option chain only for NIFTY
    if symbol != "NIFTY":
        oc_data, oc_status = [], "Option chain only available for NIFTY"
    else:
        oc_data, oc_status = get_option_chain()

    # pick priority message
    msg = ltp_status if ltp is None else oc_status if oc_data is None else "OK"

    # error overrides color
    if "Token expired" in msg:
        status_color = "warning"
    if oc_data is None or ltp is None:
        status_color = "danger"

    return (
        f"{ltp:.2f}" if ltp is not None else "--",
        history,
        oc_data or [],
        msg,
        status_color,
        f"API status: {msg}",
    )

@app.callback(
    Output("price-chart", "figure"),
    Input("price-history", "data"),
)
def update_chart(history):
    if not history:
        return go.Figure(
            layout=go.Layout(
                template="plotly_dark",
                title="Waiting for data...",
                height=400,
            )
        )
    df = pd.DataFrame(history)
    fig = go.Figure(
        data=go.Scatter(x=df["time"], y=df["price"], mode="lines+markers", line=dict(color="#29b6f6"))
    )
    fig.update_layout(template="plotly_dark", title="Live Price", height=400, margin=dict(l=20, r=20, t=40, b=20))
    return fig

# ------------------
# MAIN
# ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
