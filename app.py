import os
import requests
from dash import Dash, html, dcc, Input, Output
from dash.dash_table import DataTable

# =========================
# CONFIG
# =========================
BASE_URL = "https://api.dhan.co/v2"

SYMBOL_MAP = {
    "NIFTY": 13,
    "BANKNIFTY": 25,
    "FINNIFTY": 27
}

# =========================
# ENV
# =========================
ACCESS_TOKEN = os.getenv("DHAN_TOKEN")
CLIENT_ID = os.getenv("DHAN_CLIENT_ID")

# =========================
# API FUNCTIONS
# =========================
def get_headers():
    return {
        "access-token": ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }

def get_expiry(symbol):
    try:
        url = f"{BASE_URL}/optionchain/expirylist"
        payload = {
            "UnderlyingScrip": SYMBOL_MAP[symbol],
            "UnderlyingSeg": "IDX_I"
        }

        res = requests.post(url, json=payload, headers=get_headers())
        print("EXPIRY:", res.status_code, res.text)

        if res.status_code != 200:
            return []

        data = res.json()
        return data.get("data", [])

    except Exception as e:
        print("Expiry Error:", e)
        return []


def get_option_chain(symbol, expiry):
    try:
        url = f"{BASE_URL}/optionchain"

        payload = {
            "UnderlyingScrip": SYMBOL_MAP[symbol],
            "UnderlyingSeg": "IDX_I",
            "Expiry": expiry
        }

        res = requests.post(url, json=payload, headers=get_headers())
        print("CHAIN:", res.status_code, res.text)

        if res.status_code != 200:
            return [], f"API Error {res.status_code}"

        data = res.json()

        rows = []
        strikes = data.get("data", [])

        for item in strikes[:10]:
            rows.append({
                "Strike": item.get("strikePrice"),
                "Call OI": item.get("CE", {}).get("oi", "-"),
                "Put OI": item.get("PE", {}).get("oi", "-"),
                "Call LTP": item.get("CE", {}).get("last_price", "-"),
                "Put LTP": item.get("PE", {}).get("last_price", "-")
            })

        return rows, ""

    except Exception as e:
        return [], str(e)

# =========================
# DASH APP
# =========================
app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H2("Dhan Option Chain Dashboard"),

    dcc.Dropdown(
        id="symbol",
        options=[{"label": k, "value": k} for k in SYMBOL_MAP],
        value="NIFTY"
    ),

    dcc.Dropdown(id="expiry"),

    html.Div(id="status", style={"color": "red"}),

    DataTable(
        id="table",
        columns=[
            {"name": "Strike", "id": "Strike"},
            {"name": "Call OI", "id": "Call OI"},
            {"name": "Put OI", "id": "Put OI"},
            {"name": "Call LTP", "id": "Call LTP"},
            {"name": "Put LTP", "id": "Put LTP"},
        ]
    ),

    dcc.Interval(id="refresh", interval=5000)
])

# =========================
# CALLBACKS
# =========================
@app.callback(
    Output("expiry", "options"),
    Output("expiry", "value"),
    Input("symbol", "value")
)
def load_expiry(symbol):
    expiries = get_expiry(symbol)
    opts = [{"label": e, "value": e} for e in expiries]

    return opts, expiries[0] if expiries else None


@app.callback(
    Output("table", "data"),
    Output("status", "children"),
    Input("symbol", "value"),
    Input("expiry", "value"),
    Input("refresh", "n_intervals")
)
def update(symbol, expiry, n):
    if not ACCESS_TOKEN or not CLIENT_ID:
        return [], "Missing Token / Client ID"

    if not expiry:
        return [], "No Expiry Selected"

    return get_option_chain(symbol, expiry)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run_server(host="0.0.0.0", port=port)
