import os
from typing import Any, Dict, List, Optional, Tuple

import requests
from dash import Dash, Input, Output, dcc, html
from dash.dash_table import DataTable

# -----------------------------
# CONFIG
# -----------------------------
DHAN_OPTIONCHAIN_URL = "https://api.dhan.co/v2/optionchain"

SYMBOL_TO_SECURITY_ID = {
    "NIFTY": 13,
    "BANKNIFTY": 25,
    "FINNIFTY": 27,
}

REFRESH_MS = 5000  # 5 sec


# -----------------------------
# ENV
# -----------------------------
def get_token():
    return os.getenv("DHAN_TOKEN")


def get_client_id():
    return os.getenv("DHAN_CLIENT_ID")


# -----------------------------
# API CALL
# -----------------------------
def fetch_option_chain(security_id, token, client_id):
    url = DHAN_OPTIONCHAIN_URL

    headers = {
        "access-token": token,
        "client-id": client_id,
        "Content-Type": "application/json"
    }

    payload = {
        "UnderlyingScrip": security_id,
        "UnderlyingSeg": "IDX_I",
        "Expiry": get_expiry()
    }

    try:
        res = requests.post(url, headers=headers, json=payload)

        print("STATUS:", res.status_code)
        print("RESPONSE:", res.text)

        if res.status_code != 200:
            return None, f"API error: HTTP {res.status_code}"

        return res.json(), None

    except Exception as e:
        return None, str(e)


# -----------------------------
# AUTO EXPIRY (SIMPLE)
# -----------------------------
def get_expiry():
    # 🔥 Manually update weekly expiry (IMPORTANT)
    return "2026-04-02"


# -----------------------------
# DATA PARSE
# -----------------------------
def extract_data(data):
    try:
        chain = data.get("data", [])

        rows = []
        for item in chain:
            strike = item.get("strikePrice")

            ce = item.get("CE", {})
            pe = item.get("PE", {})

            rows.append({
                "Strike Price": strike,
                "Call OI": ce.get("openInterest", "-"),
                "Put OI": pe.get("openInterest", "-")
            })

        rows = sorted(rows, key=lambda x: x["Strike Price"])
        return rows[:5]

    except:
        return []


# -----------------------------
# DASH APP
# -----------------------------
app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H2("Options Chain Dashboard (Dhan API)"),

    dcc.Dropdown(
        id="symbol",
        options=[{"label": k, "value": k} for k in SYMBOL_TO_SECURITY_ID.keys()],
        value="NIFTY"
    ),

    html.Div(id="status", style={"color": "red"}),

    DataTable(
        id="table",
        columns=[
            {"name": "Strike Price", "id": "Strike Price"},
            {"name": "Call OI", "id": "Call OI"},
            {"name": "Put OI", "id": "Put OI"},
        ],
        data=[]
    ),

    dcc.Interval(id="interval", interval=REFRESH_MS)
])


# -----------------------------
# CALLBACK
# -----------------------------
@app.callback(
    Output("table", "data"),
    Output("status", "children"),
    Input("symbol", "value"),
    Input("interval", "n_intervals")
)
def update(symbol, n):
    token = get_token()
    client_id = get_client_id()

    if not token:
        return [], "Missing DHAN_TOKEN"

    if not client_id:
        return [], "Missing DHAN_CLIENT_ID"

    sec_id = SYMBOL_TO_SECURITY_ID.get(symbol)

    data, err = fetch_option_chain(sec_id, token, client_id)

    if err:
        return [], err

    rows = extract_data(data)

    if not rows:
        return [], "No data available"

    return rows, ""


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run_server(host="0.0.0.0", port=port)
