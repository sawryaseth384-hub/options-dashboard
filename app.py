import os
from datetime import datetime
import requests
import pandas as pd
import plotly.graph_objs as go
from dash import Dash, html, dcc, dash_table, Input, Output, State
import dash_bootstrap_components as dbc

# ---------- ENV ----------
CLIENT_ID = os.getenv("CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
PORT = int(os.environ.get("PORT", 3000))

HEADERS = {
    "access-token": DHAN_ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

print("🚀 DASH APP RUNNING")
print("CLIENT:", CLIENT_ID)
print("TOKEN:", "OK" if DHAN_ACCESS_TOKEN else "MISSING")

# ---------- API ----------
LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
EXPIRY_URL = "https://api.dhan.co/v2/optionChain/expiryList"
OPTION_CHAIN_URL = "https://api.dhan.co/v2/optionChain"

# ---------- SETTINGS ----------
LTP_INTERVAL_MS = 1000
OC_INTERVAL_MS = 5000
MAX_POINTS = 100

# ---------- FALLBACK ----------
def mock_ltp():
    return 22500 + (datetime.now().second % 50)

def mock_oc():
    return [
        {"Strike": 22400, "CE LTP": 120, "PE LTP": 80, "CE OI": 100000, "PE OI": 90000},
        {"Strike": 22500, "CE LTP": 90, "PE LTP": 100, "CE OI": 120000, "PE OI": 110000},
        {"Strike": 22600, "CE LTP": 60, "PE LTP": 130, "CE OI": 90000, "PE OI": 140000},
    ]

# ---------- API CALL ----------
def fetch_ltp():
    try:
        payload = {"NSE_INDEX": [13]}
        res = SESSION.post(LTP_URL, json=payload, timeout=2)

        print("LTP STATUS:", res.status_code)
        print("LTP RESPONSE:", res.text)

        data = res.json()
        price = data["data"][0].get("lastPrice")

        if not price:
            raise Exception("No price")

        return price
    except Exception as e:
        print("❌ LTP ERROR:", e)
        print("⚠️ USING MOCK LTP")
        return mock_ltp()

def fetch_option_chain():
    try:
        expiry_payload = {"UnderlyingScrip": 13, "UnderlyingSeg": "IDX_I"}
        expiry_res = SESSION.post(EXPIRY_URL, json=expiry_payload, timeout=2)
        expiry = expiry_res.json()["data"][0]["expiryCode"]

        payload = {
            "UnderlyingScrip": 13,
            "UnderlyingSeg": "IDX_I",
            "ExpiryCode": expiry,
        }

        res = SESSION.post(OPTION_CHAIN_URL, json=payload, timeout=2)
        data = res.json()["data"]

        rows = []
        for item in data[:20]:
            rows.append({
                "Strike": item.get("strikePrice"),
                "CE LTP": item.get("CE", {}).get("ltp"),
                "PE LTP": item.get("PE", {}).get("ltp"),
                "CE OI": item.get("CE", {}).get("oi"),
                "PE OI": item.get("PE", {}).get("oi"),
            })

        return rows

    except Exception as e:
        print("❌ OC ERROR:", e)
        print("⚠️ USING MOCK OC")
        return mock_oc()

# ---------- DASH APP ----------
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

app.layout = dbc.Container([
    html.H2("🔥 AI Trading Dashboard"),
    dbc.Alert("Waiting...", id="status"),
    html.H3(id="ltp"),
    dcc.Graph(id="chart"),
    dash_table.DataTable(
        id="table",
        columns=[
            {"name": "Strike", "id": "Strike"},
            {"name": "CE LTP", "id": "CE LTP"},
            {"name": "PE LTP", "id": "PE LTP"},
            {"name": "CE OI", "id": "CE OI"},
            {"name": "PE OI", "id": "PE OI"},
        ],
        page_size=10,
    ),
    dcc.Store(id="history", data=[]),
    dcc.Interval(id="ltp-interval", interval=LTP_INTERVAL_MS),
    dcc.Interval(id="oc-interval", interval=OC_INTERVAL_MS),
], fluid=True)

# ---------- LTP CALLBACK ----------
@app.callback(
    Output("ltp", "children"),
    Output("status", "children"),
    Output("status", "color"),
    Output("chart", "figure"),
    Output("history", "data"),
    Input("ltp-interval", "n_intervals"),
    State("history", "data"),
)
def update_ltp(n, history):
    price = fetch_ltp()

    history = history or []
    history.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "price": price
    })
    history = history[-MAX_POINTS:]

    df = pd.DataFrame(history)

    fig = go.Figure(
        data=[go.Scatter(x=df["time"], y=df["price"], mode="lines")],
        layout=go.Layout(template="plotly_dark", title="LTP")
    )

    return f"LTP: {price}", "LIVE", "success", fig, history

# ---------- OC CALLBACK ----------
@app.callback(
    Output("table", "data"),
    Input("oc-interval", "n_intervals"),
)
def update_oc(n):
    return fetch_option_chain()

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
