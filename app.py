import json
import requests
from dash import Dash, html, dcc, Input, Output

# ------------------ APP INIT ------------------
app = Dash(__name__)
server = app.server

# ------------------ LAYOUT ------------------
app.layout = html.Div([
    html.H1("Options Dashboard"),

    dcc.Dropdown(
        id="symbol",
        options=[
            {"label": "NIFTY", "value": "NIFTY"},
            {"label": "BANKNIFTY", "value": "BANKNIFTY"}
        ],
        value="NIFTY"
    ),

    html.H3(id="ltp"),

    html.Table(id="option-table"),

    html.Pre(id="raw-json"),

    dcc.Interval(id="interval", interval=2000, n_intervals=0)
])

# ------------------ NSE SESSION ------------------
def get_session():
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    }
    session.get("https://www.nseindia.com", headers=headers)
    return session, headers

# ------------------ LTP ------------------
def get_ltp(symbol):
    try:
        session, headers = get_session()

        url = f"https://www.nseindia.com/api/quote-derivative?symbol={symbol}"
        response = session.get(url, headers=headers, timeout=5)

        data = response.json()
        return data.get("underlyingValue", "N/A")

    except Exception as e:
        return f"Error: {e}"

# ------------------ OPTION CHAIN ------------------
def get_option_chain(symbol):
    try:
        session, headers = get_session()

        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        response = session.get(url, headers=headers, timeout=5)

        data = response.json()
        rows = data["records"]["data"][:5]

        table = [
            html.Tr([
                html.Th("Strike"),
                html.Th("Call OI"),
                html.Th("Put OI")
            ])
        ]

        for row in rows:
            strike = row.get("strikePrice", "-")

            call_oi = row.get("CE", {}).get("openInterest", "-")
            put_oi = row.get("PE", {}).get("openInterest", "-")

            table.append(
                html.Tr([
                    html.Td(str(strike)),
                    html.Td(str(call_oi)),
                    html.Td(str(put_oi))
                ])
            )

        return table, data

    except Exception as e:
        return [html.Tr([html.Td("Error loading data")])], {"error": str(e)}

# ------------------ CALLBACK ------------------
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
    try:
        ltp = get_ltp(symbol)
        ltp_text = f"{symbol} LTP: {ltp}"

        table_children, raw_output = get_option_chain(symbol)

        return ltp_text, table_children, json.dumps(raw_output, indent=2)

    except Exception as e:
        return "Error", [], str(e)

# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(debug=True)
