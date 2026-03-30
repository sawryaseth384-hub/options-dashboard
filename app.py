import os
from typing import Any, Dict, List, Optional, Tuple

import requests
from dash import Dash, Input, Output, dcc, html
from dash.dash_table import DataTable

# -----------------------------
# Configuration / Constants
# -----------------------------
DHAN_OPTIONCHAIN_URL = "https://api.dhan.co/market/v2/option-chain"

SYMBOL_TO_SECURITY_ID: Dict[str, int] = {
    "NIFTY": 13,
    "BANKNIFTY": 25,
    "FINNIFTY": 27,
}

REFRESH_MS = 5_000  # 5 seconds


# -----------------------------
# Token + API helpers
# -----------------------------
def get_dhan_token() -> Optional[str]:
    """Read DHAN token from environment."""
    token = os.getenv("DHAN_TOKEN")
    return token.strip() if token and token.strip() else None


def fetch_option_chain(security_id: int, token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Fetch option chain data from Dhan API.

    Returns:
      (json_data, error_message)
      - If request succeeds and JSON parses => (data, None)
      - If API / parsing error => (None, error_message)
    """
    headers = {
        "access-token": token,
        "Content-Type": "application/json",
    }
    payload = {
        "underlyingScrip": security_id,
        "exchangeSegment": "IDX_I",
    }

    try:
        resp = requests.post(DHAN_OPTIONCHAIN_URL, headers=headers, json=payload, timeout=15)
    except requests.RequestException as e:
        # Not specified in your required messages; keep it informative but consistent.
        return None, f"Request error: {e}"

    # IMPORTANT FIX: debug logs
    print(resp.status_code)
    print(resp.text)

    if resp.status_code != 200:
        # Requirement: "show status code"
        return None, f"API error: HTTP {resp.status_code}"

    try:
        return resp.json(), None
    except ValueError:
        return None, "API error: Invalid JSON response"


# -----------------------------
# JSON parsing / normalization
# -----------------------------
def _walk_find_first_list(node: Any, max_depth: int = 6) -> Optional[List[Any]]:
    """
    Best-effort: find the first list-like node within a nested dict/list structure.
    This helps handle multiple possible JSON structures without relying on one schema.
    """
    if max_depth < 0:
        return None

    if isinstance(node, list):
        return node

    if isinstance(node, dict):
        # common keys sometimes holding the strike list
        preferred_keys = ("strikes", "strikeData", "chain", "optionChain", "data", "oc", "records", "result")
        for k in preferred_keys:
            if k in node:
                found = _walk_find_first_list(node[k], max_depth=max_depth - 1)
                if found is not None:
                    return found

        # fallback: scan all values
        for v in node.values():
            found = _walk_find_first_list(v, max_depth=max_depth - 1)
            if found is not None:
                return found

    return None


def extract_top_5_strikes(option_chain_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract and normalize the top 5 strikes into rows:
      Strike Price, Call OI, Put OI

    Handles multiple JSON shapes and multiple field possibilities:
      strikePrice (or strike/strike_price)
      callOI OR CE.openInterest (plus a few variants)
      putOI  OR PE.openInterest (plus a few variants)
    """
    strikes = _walk_find_first_list(option_chain_json)

    if not strikes or not isinstance(strikes, list):
        return []

    rows: List[Dict[str, Any]] = []

    for item in strikes:
        if not isinstance(item, dict):
            continue

        strike = item.get("strikePrice") or item.get("strike") or item.get("strike_price")

        ce = item.get("CE") or item.get("ce") or item.get("call")
        pe = item.get("PE") or item.get("pe") or item.get("put")

        call_oi = None
        put_oi = None

        # call OI: prefer callOI or CE.openInterest
        call_oi = item.get("callOI") or item.get("call_oi")
        if call_oi is None and isinstance(ce, dict):
            call_oi = ce.get("openInterest") or ce.get("oi") or ce.get("open_interest")

        # put OI: prefer putOI or PE.openInterest
        put_oi = item.get("putOI") or item.get("put_oi")
        if put_oi is None and isinstance(pe, dict):
            put_oi = pe.get("openInterest") or pe.get("oi") or pe.get("open_interest")

        if strike is None:
            continue

        rows.append(
            {
                "Strike Price": strike,
                "Call OI": call_oi if call_oi is not None else "-",
                "Put OI": put_oi if put_oi is not None else "-",
            }
        )

    def strike_sort_key(r: Dict[str, Any]) -> float:
        try:
            return float(r["Strike Price"])
        except Exception:
            return float("inf")

    rows.sort(key=strike_sort_key)
    return rows[:5]


# -----------------------------
# Dash App (Railway-ready)
# -----------------------------
app = Dash(__name__, title="Options Chain Dashboard (Dhan)")
server = app.server  # Required for Gunicorn: app:server

app.layout = html.Div(
    style={
        "maxWidth": "980px",
        "margin": "40px auto",
        "padding": "0 16px",
        "fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
    },
    children=[
        html.Div(
            style={
                "display": "flex",
                "flexDirection": "column",
                "gap": "6px",
                "marginBottom": "18px",
            },
            children=[
                html.H2("Options Chain Dashboard (Dhan API)", style={"margin": 0}),
                html.Div("Auto-refreshes every 5 seconds.", style={"color": "#666"}),
            ],
        ),
        html.Div(
            style={
                "display": "flex",
                "flexWrap": "wrap",
                "gap": "12px",
                "alignItems": "center",
                "marginBottom": "12px",
                "padding": "12px",
                "border": "1px solid #eee",
                "borderRadius": "12px",
                "background": "#fff",
                "boxShadow": "0 1px 8px rgba(0,0,0,0.04)",
            },
            children=[
                html.Label("Select Index:", style={"fontWeight": 700}),
                dcc.Dropdown(
                    id="index-dropdown",
                    options=[{"label": k, "value": k} for k in SYMBOL_TO_SECURITY_ID.keys()],
                    value="NIFTY",
                    clearable=False,
                    style={"width": "260px"},
                ),
                html.Div(
                    id="status-text",
                    style={"color": "#b00020", "fontWeight": 700, "marginLeft": "6px"},
                ),
            ],
        ),
        DataTable(
            id="options-table",
            columns=[
                {"name": "Strike Price", "id": "Strike Price"},
                {"name": "Call OI", "id": "Call OI"},
                {"name": "Put OI", "id": "Put OI"},
            ],
            data=[],
            style_table={
                "overflowX": "auto",
                "border": "1px solid #eee",
                "borderRadius": "12px",
            },
            style_header={
                "fontWeight": "800",
                "backgroundColor": "#f7f7f9",
                "borderBottom": "1px solid #e9e9ee",
                "padding": "12px",
            },
            style_cell={
                "padding": "12px",
                "borderBottom": "1px solid #f0f0f0",
                "fontSize": "14px",
            },
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#fcfcff"},
            ],
        ),
        dcc.Interval(id="refresh-interval", interval=REFRESH_MS, n_intervals=0),
        html.Div(
            style={"marginTop": "10px", "color": "#777", "fontSize": "12px"},
            children=[
                "Note: Server logs include Dhan API response status_code and response body for debugging."
            ],
        ),
    ],
)


@app.callback(
    Output("options-table", "data"),
    Output("status-text", "children"),
    Input("index-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_table(selected_index: str, _n: int):
    """
    Update table every REFRESH_MS and when dropdown changes.

    Error handling requirements:
    - Missing DHAN_TOKEN -> "Missing DHAN_TOKEN"
    - API error -> show status code
    - Empty data -> "No data available"
    """
    token = get_dhan_token()
    if not token:
        return [], "Missing DHAN_TOKEN"

    security_id = SYMBOL_TO_SECURITY_ID.get(selected_index)
    if security_id is None:
        return [], "Invalid index selection"

    json_data, err = fetch_option_chain(security_id=security_id, token=token)
    if err:
        return [], err

    rows = extract_top_5_strikes(json_data or {})
    if not rows:
        return [], "No data available"

    return rows, ""


# -----------------------------
# Local dev entrypoint (Railway compatible)
# -----------------------------
if __name__ == "__main__":
    # Railway provides PORT; default to 8080 per your requirement.
    port = int(os.getenv("PORT", 8080))
    app.run_server(host="0.0.0.0", port=port, debug=False)
