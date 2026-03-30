import json
from dash import Dash, html, dcc, Input, Output

# Initialize app
app = Dash(__name__)
server = app.server

# Layout
app.layout = html.Div([
    html.H2("Options Dashboard"),

    dcc.Dropdown(
        id="symbol",
        options=[
            {"label": "NIFTY", "value": "NIFTY"},
            {"label": "BANKNIFTY", "value": "BANKNIFTY"}
        ],
        value="NIFTY"
    ),

    dcc.Interval(
        id="interval",
        interval=2000,  # 2 sec
        n_intervals=0
    ),

    html.H3(id="ltp"),

    html.Table(id="option-table"),

    html.Pre(id="raw-json")
])


# Callback
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
    ltp_text = f"{symbol} LTP: Loading..."
    
    # Dummy table (safe)
    table_children = [
        html.Tr([
            html.Th("Strike"),
            html.Th("Call OI"),
            html.Th("Put OI")
        ]),
        html.Tr([
            html.Td("22000"),
            html.Td("1000"),
            html.Td("1200")
        ])
    ]

    raw_output = {
        "status": "running",
        "symbol": symbol,
        "interval": n
    }

    return ltp_text, table_children, json.dumps(raw_output, indent=2)


# Run (for local)
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
