"""
Dhan Trading Dashboard (Dash)
- No Streamlit, no TOTP; uses only env vars CLIENT_ID & DHAN_ACCESS_TOKEN
- Headers: access-token, client-id, Content-Type
- Endpoints: /v2/marketfeed/ltp, /v2/optionChain/expiryList, /v2/optionChain
- Auto-refresh every 5 seconds
"""

import os
import datetime as dt
from typing import Optional, Tuple, List, Dict

import requests
import dash
from dash import Dash, dcc, html, Input, Output, State
import dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# ------------------ Config ------------------
CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "").strip()
if not CLIENT_ID or not TOKEN:
    raise SystemExit("Missing env vars: set CLIENT_ID and DHAN_ACCESS_TOKEN before running.")

HEADERS = {
    "access-token": TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
}

BASE_URL = "https://api.dhan.co/v2"
REFRESH_MS = 5000

SYMBOLS = {
    "NIFTY": {"security_id": 13, "segment": "NSE_INDEX", "ltp_key": "NSE_INDEX", "seg_opt": "IDX_I"},
    "RELIANCE": {"security_id": 2885, "segment": "NSE_EQ", "ltp_key": "NSE_EQ", "seg_opt": "NSE_EQ"},
}


# ------------------ HTTP Helper ------------------
def _post(endpoint: str, payload: dict) -> Tuple[Optional[dict], Optional[str], Optional[int]]:
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    try:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        if resp.status_code == 401:
            return None, "Token expired — update DHAN_ACCESS_TOKEN", resp.status_code
        if resp.status_code >= 400:
            return None, f"API error ({resp.status_code}): {data}", resp.status_code
        return data, None, resp.status_code
    except Exception as e:
        return None, f"Network error: {e}", None


# ------------------ API Wrappers ------------------
def get_ltp(security_id: int, ltp_key: str) -> Tuple[Optional[float], Optional[str]]:
    payload = {ltp_key: [security_id]}
    data, err, _ = _post("marketfeed/ltp", payload)
    if err:
        return None, err
    ltp_val = None
    if isinstance(data, dict):
        d = data.get("data", data)
        if isinstance(d, list) and d:
            rec = d[0]
            ltp_val = rec.get("ltp") or rec.get("lastPrice") or rec.get("price")
        elif isinstance(d, dict):
            ltp_val = d.get("ltp") or d.get("lastPrice") or d.get("price")
    if ltp_val is None:
        return None, "LTP missing in response"
    return float(ltp_val), None


def get_expiry_list(security_id: int, seg_opt: str) -> Tuple[Optional[List[str]], Optional[str]]:
    payload = {"UnderlyingScrip": int(security_id), "UnderlyingSeg": seg_opt}
    data, err, _ = _post("optionChain/expiryList", payload)
    if err:
        return None, err
    expiries = []
    if isinstance(data, dict):
        d = data.get("data", data)
        for key in ("expiries", "expiryList", "expiry", "items"):
            val = d.get(key) if isinstance(d, dict) else None
            if isinstance(val, list):
                expiries = [str(x) for x in val if x]
                break
    if not expiries:
        return None, "Expiry API failed due to authentication or payload issue"
    return expiries, None


def get_option_chain(security_id: int, seg_opt: str) -> Tuple[Optional[List[Dict]], Optional[str], Optional[str]]:
    expiries, err = get_expiry_list(security_id, seg_opt)
    if err:
        return None, err, None
    expiry = expiries[0] if expiries else None
    if not expiry:
        return None, "Expiry API failed due to authentication or payload issue", None

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": seg_opt,
        "Expiry": str(expiry),
    }
    data, err, _ = _post("optionChain", payload)
    if err:
        return None, err, expiry

    rows = []
    core = data.get("data", data) if isinstance(data, dict) else data
    if isinstance(core, list):
        for item in core:
            strike = item.get("strikePrice") or item.get("strike") or item.get("strike_price")
            ce = item.get("CE", {}).get("ltp") if isinstance(item.get("CE"), dict) else item.get("ceLtp") or item.get("CE")
            pe = item.get("PE", {}).get("ltp") if isinstance(item.get("PE"), dict) else item.get("peLtp") or item.get("PE")
            if strike is not None:
                rows.append({"Strike": strike, "CE LTP": ce, "PE LTP": pe})
    elif isinstance(core, dict):
        for strike, legs in core.items():
            ce = legs.get("CE", {}).get("ltp") if isinstance(legs.get("CE"), dict) else legs.get("CE")
            pe = legs.get("PE", {}).get("ltp") if isinstance(legs.get("PE"), dict) else legs.get("PE")
            rows.append({"Strike": strike, "CE LTP": ce, "PE LTP": pe})
    return rows, None, expiry


# ------------------ Dash App ------------------
app: Dash = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True,
)
app.title = "Dhan Trading Dashboard"

app.layout = dbc.Container(
    [
        html.H2("Dhan Trading Dashboard", className="text-center my-3"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div("Symbol", className="fw-bold"),
                        dcc.Dropdown(
                            id="symbol-dropdown",
                            options=[{"label": k, "value": k} for k in SYMBOLS.keys()],
                            value="NIFTY",
                            clearable=False,
                            style={"color": "#000"},
                        ),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        html.Div("Live LTP", className="fw-bold"),
                        html.H3(id="ltp-display", className="text-success"),
                        html.Div(id="status-display", className="small text-danger"),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        html.Div("Debug Panel", className="fw-bold"),
                        html.Div(id="debug-panel", className="small"),
                    ],
                    md=6,
                ),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    dash_table.DataTable(
                        id="oc-table",
                        columns=[
                            {"name": "Strike", "id": "Strike"},
                            {"name": "CE LTP", "id": "CE LTP"},
                            {"name": "PE LTP", "id": "PE LTP"},
                        ],
                        data=[],
                        style_table={"overflowX": "auto"},
                        style_header={"backgroundColor": "#1f2c56", "color": "white", "fontWeight": "bold"},
                        style_cell={"backgroundColor": "#111", "color": "white"},
                    ),
                    md=6,
                ),
                dbc.Col(
                    dcc.Graph(id="price-chart", figure=go.Figure()),
                    md=6,
                ),
            ]
        ),
        dcc.Interval(id="refresh-interval", interval=REFRESH_MS, n_intervals=0),
        dcc.Store(id="price-history", data=[]),
    ],
    fluid=True,
)


# ------------------ Callbacks ------------------
@app.callback(
    Output("ltp-display", "children"),
    Output("status-display", "children"),
    Output("oc-table", "data"),
    Output("price-chart", "figure"),
    Output("price-history", "data"),
    Input("refresh-interval", "n_intervals"),
    State("symbol-dropdown", "value"),
    State("price-history", "data"),
)
def refresh_data(n, symbol, history):
    info = SYMBOLS[symbol]

    # LTP
    ltp, ltp_err = get_ltp(info["security_id"], info["ltp_key"])
    if ltp_err:
        return "", ltp_err, [], go.Figure(), history

    # History for chart
    history = (history or [])
    history.append({"t": dt.datetime.now().isoformat(), "p": ltp})
    history = history[-120:]

    # Option Chain
    oc_rows, oc_err, expiry = get_option_chain(info["security_id"], info["seg_opt"])
    status = oc_err or f"OK (Expiry: {expiry})"

    # Chart
    fig = go.Figure()
    if history:
        fig.add_trace(go.Scatter(x=[h["t"] for h in history], y=[h["p"] for h in history],
                                 mode="lines+markers", name="LTP"))
    fig.update_layout(template="plotly_dark", margin=dict(l=10, r=10, t=30, b=10))

    return f"{ltp:.2f}", status, oc_rows or [], fig, history


@app.callback(Output("debug-panel", "children"), Input("refresh-interval", "n_intervals"))
def debug_info(_):
    masked_token = TOKEN[:4] + "..." + TOKEN[-4:] if len(TOKEN) > 8 else TOKEN
    masked_client = CLIENT_ID[:4] + "..." + CLIENT_ID[-4:] if len(CLIENT_ID) > 8 else CLIENT_ID
    return f"CLIENT_ID: {masked_client} | TOKEN: {masked_token}"


# ------------------ Entry ------------------
if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=False)
