import os
import requests
from dash import Dash, html, dcc
from dash.dependencies import Input, Output

# =========================
# ENV VARIABLES (Railway)
# =========================
DHAN_TOKEN = os.getenv("DHAN_TOKEN")

# =========================
# SYMBOL MAP
# =========================
symbol_map = {
    "NIFTY": 13,
    "BANKNIFTY": 25,
    "FINNIFTY": 27
}

# =========================
# DASH APP
# =========================
app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H2("Option Chain Dashboard"),

    dcc.Dropdown(
        id="symbol",
        options=[
            {"label": "NIFTY", "value": "NIFTY"},
            {"label": "BANKNIFTY", "value": "BANKNIFTY"},
            {"label": "FINNIFTY", "value": "FINNIFTY"},
        ],
        value="NIFTY"
    ),

    html.Br(),

    html.Table(id="option-table"),

    dcc.Interval(id="interval", interval=5000, n_intervals=0)
])

# =========================
# API FUNCTION
# =========================
def get_option_chain(symbol):
    try:
        security_id = symbol_map.get(symbol, 13)

        url = "https://api.dhan.co/market/v2/option-chain"

        headers = {
            "access-token": DHAN_TOKEN,
            "Content-Type": "application/json"
        }

        payload = {
            "underlyingScrip": security_id,
            "exchangeSegment": "IDX_I"
        }

        res = requests.post(url, json=payload, headers=headers)
        data = res.json()

        rows = data.get("data", [])[:5]

        table = [
            html.Tr([
                html.Th("Strike"),
                html.Th("Call OI"),
                html.Th("Put OI")
            ])
        ]

        for row in rows:
            table.append(
                html.Tr([
                    html.Td(str(row.get("strikePrice", "-"))),
                    html.Td(str(row.get("callOI", "-"))),
                    html.Td(str(row.get("putOI", "-")))
                ])
            )

        return table

    except Exception as e:
        return [html.Tr([html.Td(f"Error: {str(e)}")])]

# =========================
# CALLBACK
# =========================
@app.callback(
    Output("option-table", "children"),
    Input("symbol", "value"),
    Input("interval", "n_intervals")
)
def update_table(symbol, n):
    return get_option_chain(symbol)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
