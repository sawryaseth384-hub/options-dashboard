import os
import requests
import dash
from dash import dcc, html, Input, Output
import pandas as pd

app = dash.Dash(__name__)
server = app.server

# =========================
# NSE HEADERS (IMPORTANT)
# =========================
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br"
}

# =========================
# LAYOUT
# =========================
app.layout = html.Div([
    html.H2("Options Dashboard"),

    html.Div(id="ltp", style={"fontSize": "24px"}),

    dcc.Interval(id="interval", interval=5000, n_intervals=0),

    dcc.Dropdown(
        id="symbol",
        options=[
            {"label": "NIFTY", "value": "NIFTY"},
            {"label": "BANKNIFTY", "value": "BANKNIFTY"},
        ],
        value="NIFTY"
    ),

    html.Table(id="option-table"),

    # ===== DEBUG PANEL =====
    html.H3("DEBUG API DATA"),
    html.Pre(
        id="raw-json",
        style={
            "height": "300px",
            "overflow": "scroll",
            "backgroundColor": "black",
            "color": "lime",
            "padding": "10px"
        }
    )
])

# =========================
# CALLBACK
# =========================
@app.callback(
    [
        Output("ltp", "children"),
        Output("option-table", "children"),
        Output("raw-json", "children")
    ],
    [
        Input("interval", "n_intervals"),
        Input("symbol", "value")
    ]
)
def update_dashboard(n, symbol):
    raw_output = ""

    try:
        session = requests.Session()

        # Step 1: NSE session init
        session.get("https://www.nseindia.com", headers=HEADERS)

        # =========================
        # OPTION CHAIN API
        # =========================
        chain_url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        chain_response = session.get(chain_url, headers=HEADERS)

        raw_output += "\n\n--- OPTION CHAIN RESPONSE ---\n"
        raw_output += chain_response.text

        data = chain_response.json()

        records = data.get("records", {})
        underlying = records.get("underlyingValue", "N/A")

        ltp_value = f"LTP: {underlying}"

        # =========================
        # TABLE BUILD
        # =========================
        rows = records.get("data", [])

        table_header = html.Tr([
            html.Th("Strike"),
            html.Th("CE OI"),
            html.Th("PE OI")
        ])

        table_rows = []

        for row in rows[:10]:
            strike = row.get("strikePrice", "")

            ce_oi = row.get("CE", {}).get("openInterest", "") if row.get("CE") else ""
            pe_oi = row.get("PE", {}).get("openInterest", "") if row.get("PE") else ""

            table_rows.append(
                html.Tr([
                    html.Td(strike),
                    html.Td(ce_oi),
                    html.Td(pe_oi)
                ])
            )

        table = [table_header] + table_rows

        return ltp_value, table, raw_output

    except Exception as e:
        raw_output += "\n\nERROR:\n" + str(e)
        return "Error loading data", [html.Tr([html.Td("Error")])], raw_output


# =========================
# RUN (RAILWAY SAFE)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port)
