import os
import requests
import dash
from dash import dcc, html, Input, Output
import pandas as pd

app = dash.Dash(__name__)
server = app.server  # Railway ke liye important

# =========================
# LAYOUT
# =========================
app.layout = html.Div([
    html.H2("Options Dashboard"),

    html.Div(id="ltp", style={"fontSize": "24px", "marginBottom": "10px"}),

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
        # =========================
        # LTP API (example)
        # =========================
        ltp_url = f"https://api.example.com/ltp?symbol={symbol}"
        response = requests.get(ltp_url)

        raw_output += "\n\n--- LTP RESPONSE ---\n"
        raw_output += response.text

        ltp_data = response.json()
        ltp_value = f"LTP: {ltp_data.get('ltp', 'N/A')}"

        # =========================
        # EXPIRY API (example)
        # =========================
        expiry_url = f"https://api.example.com/expiry?symbol={symbol}"
        expiry_response = requests.get(expiry_url)

        raw_output += "\n\n--- EXPIRY RESPONSE ---\n"
        raw_output += expiry_response.text

        expiry_data = expiry_response.json()
        expiry = expiry_data.get("expiry", "")

        # =========================
        # OPTION CHAIN API (example)
        # =========================
        chain_url = f"https://api.example.com/chain?symbol={symbol}&expiry={expiry}"
        chain_response = requests.get(chain_url)

        raw_output += "\n\n--- OPTION CHAIN RESPONSE ---\n"
        raw_output += chain_response.text

        chain_data = chain_response.json()

        # =========================
        # TABLE BUILD
        # =========================
        df = pd.DataFrame(chain_data.get("data", []))

        if df.empty:
            table = html.Tr([html.Td("No Data")])
        else:
            table = [
                html.Tr([html.Th(col) for col in df.columns])
            ] + [
                html.Tr([html.Td(df.iloc[i][col]) for col in df.columns])
                for i in range(min(len(df), 10))
            ]

        return ltp_value, table, raw_output

    except Exception as e:
        raw_output += "\n\nERROR:\n" + str(e)
        return "Error loading data", html.Tr([html.Td("Error")]), raw_output


# =========================
# RUN (RAILWAY SAFE)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port)
