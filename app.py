import os
from typing import Any, Dict, List, Optional, Tuple

import requests
from dash import Dash, Input, Output, dcc, html
from dash.dash_table import DataTable

# -----------------------------
# Configuration / Constants
# -----------------------------
DHAN_OPTIONCHAIN_URL = "https://api.dhan.co/v2/optionchain"

# Symbol mapping (as per your requirement)
SYMBOL_TO_SECURITY_ID = {
    "NIFTY": 13,
    "BANKNIFTY": 25,
    "FINNIFTY": 27,
}

REFRESH_MS = 5_000  # 5 seconds


# -----------------------------
# Dhan API client helpers
# -----------------------------
def get_dhan_token() -> Optional[str]:
    """Read DHAN token from environment."""
    token = os.getenv("DHAN_TOKEN")
    return token.strip() if token else None


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
        "exchangeSegment": "IDX",
    }

    try:
        resp = requests.post(DHAN_OPTIONCHAIN_URL, headers=headers, json=payload, timeout=10)
    except requests.RequestException as e:
        return None, f"Request error: {e}"

    if resp.status_code != 200:
        # Requirement: "show status code"
        return None, f"API error: HTTP {resp.status_code}"

    try:
        return resp.json(), None
    except ValueError:
        return None, "API error: Invalid JSON response"


def extract_top_5_strikes(option_chain_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract and normalize the top 5 strikes into rows:
      Strike Price, Call OI, Put OI

    Note:
    Dhan's exact JSON shape can vary across accounts/versions. This function
    is defensive and tries common structures.
    """
    # Try a few likely locations for the strike list
    candidates = []

    if isinstance(option_chain_json, dict):
        # Common patterns: data -> oc / optionChain / records -> data, etc.
        for keypath in [
            ("data",),
            ("data", "oc"),
            ("data", "optionChain"),
            ("optionChain",),
            ("records", "data"),
            ("records",),
            ("result",),
        ]:
            node = option_chain_json
            ok = True
            for k in keypath:
                if isinstance(node, dict) and k in node:
                    node = node[k]
                else:
                    ok = False
                    break
            if ok:
                candidates.append(node)

    # Find the first candidate that looks like a list of strikes/dicts
    strikes = None
    for c in candidates:
        if isinstance(c, list):
            strikes = c
            break
        # Sometimes nested dict contains "strikes" or similar
        if isinstance(c, dict):
            for k in ("strikes", "strikeData", "chain", "optionChain"):
                if k in c and isinstance(c[k], list):
                    strikes = c[k]
                    break
        if strikes is not None:
            break

    if not strikes or not isinstance(strikes, list):
        return []

    # Normalize rows defensively
    rows = []
    for item in strikes:
        if not isinstance(item, dict):
            continue

        strike = item.get("strikePrice") or item.get("strike") or item.get("strike_price")
        ce = item.get("CE") or item.get("ce") or item.get("call")
        pe = item.get("PE") or item.get("pe") or item.get("put")

        # OI can be nested or flat
        call_oi = None
        put_oi = None

        if isinstance(ce, dict):
            call_oi = ce.get("openInterest") or ce.get("oi") or ce.get("open_interest")
        else:
            call_oi = item.get("callOI") or item.get("call_oi")

        if isinstance(pe, dict):
            put_oi = pe.get("openInterest") or pe.get("oi") or pe.get("open_interest")
        else:
            put_oi = item.get("putOI") or item.get("put_oi")

        # If strike is missing, skip row
        if strike is None:
            continue

        rows.append(
            {
                "Strike Price": strike,
                "Call OI": call_oi if call_oi is not None else "-",
                "Put OI": put_oi if put_oi is not None else "-",
            }
        )

    # Sort by strike price (numeric if possible), then take top 5
    def strike_sort_key(r: Dict[str, Any]) -> float:
        try:
            return float(r["Strike Price"])
        except Exception:
            return float("inf")

    rows.sort(key=strike_sort_key)
    return rows[:5]


# -----------------------------
# Dash App
# -----------------------------
app = Dash(__name__, title="Options Chain Dashboard (Dhan)")
server = app.server  # Required for Gunicorn: app:server


app.layout = html.Div(
    style={
        "maxWidth": "900px",
        "margin": "40px auto",
        "fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
    },
    children=[
        html.H2("Options Chain Dashboard (Dhan API)", style={"marginBottom": "8px"}),
        html.Div(
            "Auto-refreshes every 5 seconds.",
            style={"color": "#555", "marginBottom": "20px"},
        ),
        html.Div(
            style={"display": "flex", "gap": "12px", "alignItems": "center", "marginBottom": "16px"},
            children=[
                html.Label("Select Index:", style={"fontWeight": 600}),
                dcc.Dropdown(
                    id="index-dropdown",
                    options=[{"label": k, "value": k} for k in SYMBOL_TO_SECURITY_ID.keys()],
                    value="NIFTY",
                    clearable=False,
                    style={"width": "240px"},
                ),
                html.Div(id="status-text", style={"color": "#b00020", "fontWeight": 600}),
            ],
        ),
        DataTable(
            id="options-table",
            columns=[
                {"name": "Strike Price", "id": "Strike Price", "type": "numeric"},
                {"name": "Call OI", "id": "Call OI"},
                {"name": "Put OI", "id": "Put OI"},
            ],
            data=[],
            style_table={"overflowX": "auto", "border": "1px solid #eee"},
            style_header={"fontWeight": "700", "backgroundColor": "#f8f8f8"},
            style_cell={"padding": "10px", "borderBottom": "1px solid #eee"},
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#fcfcfc"},
            ],
        ),
        dcc.Interval(id="refresh-interval", interval=REFRESH_MS, n_intervals=0),
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
# Local dev entrypoint
# -----------------------------
if __name__ == "__main__":
    # Railway provides PORT; default to 8050 for local dev.
    port = int(os.getenv("PORT", "8050"))
    app.run_server(host="0.0.0.0", port=port, debug=False)
