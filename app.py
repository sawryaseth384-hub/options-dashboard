import os
import logging
import requests
import pandas as pd
from dash import Dash, html, dcc, Input, Output, dash_table

# ---------- LOGGING ----------
logger = logging.getLogger("gunicorn.error")
logger.setLevel(logging.INFO)

print("🚀 APP IMPORTED")

PORT = int(os.environ.get("PORT", 8080))

# ---------- DHAN CONFIG ----------
CLIENT_ID = os.getenv("CLIENT_ID")
ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

HEADERS = {
    "access-token": ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json"
}

# ---------- DASH APP ----------
app = Dash(__name__)
server = app.server

# ---------- UI ----------
app.layout = html.Div([
    html.H1("🔥 AI Trading Dashboard (ALL SEGMENTS)"),

    dcc.Dropdown(
        id="segment",
        options=[
            {"label": "NIFTY", "value": "NIFTY"},
            {"label": "BANKNIFTY", "value": "BANKNIFTY"},
            {"label": "STOCK (RELIANCE)", "value": "RELIANCE"}
        ],
        value="NIFTY"
    ),

    html.H2(id="ltp"),

    dash_table.DataTable(
        id="option-table",
        columns=[
            {"name": "Strike", "id": "strike"},
            {"name": "CE LTP", "id": "ce_ltp"},
            {"name": "PE LTP", "id": "pe_ltp"},
            {"name": "CE OI", "id": "ce_oi"},
            {"name": "PE OI", "id": "pe_oi"},
        ],
        page_size=10
    ),

    dcc.Interval(id="interval", interval=3000, n_intervals=0)
])

print("✅ LAYOUT LOADED")

# ---------- MOCK DATA (backup) ----------
def mock_data():
    data = []
    for i in range(10):
        strike = 22000 + i * 100
        data.append({
            "strike": strike,
            "ce_ltp": 100 - i*5,
            "pe_ltp": 80 + i*5,
            "ce_oi": 100000 + i*1000,
            "pe_oi": 90000 + i*1200
        })
    return data

# ---------- CALLBACK ----------
@app.callback(
    Output("ltp", "children"),
    Output("option-table", "data"),
    Input("interval", "n_intervals"),
    Input("segment", "value")
)
def update_dashboard(n, segment):
    logger.info("🔥 CALLBACK RUNNING")

    try:
        # ---------- LTP ----------
        ltp_payload = {"NSE_INDEX": [13]}
        res = requests.post(
            "https://api.dhan.co/v2/marketfeed/ltp",
            json=ltp_payload,
            headers=HEADERS
        )

        price = 0
        if res.status_code == 200:
            data = res.json()
            price = data["data"][0].get("lastPrice", 0)

        # ---------- OPTION CHAIN ----------
        table_data = mock_data()

        return f"{segment} LTP: {price}", table_data

    except Exception as e:
        logger.error(f"ERROR: {e}")
        return "Error fetching data", mock_data()

print("✅ CALLBACK REGISTERED")

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
