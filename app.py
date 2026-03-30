import os
DHAN_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
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
        import requests

        security_id = symbol_map.get(symbol, 13)

        url = "https://api.dhan.co/market/v2/ltp"

        headers = {
            "access-token": DHAN_TOKEN,
            "Content-Type": "application/json"
        }

        payload = {
            "IDX_I": [security_id]
        }

        res = requests.post(url, json=payload, headers=headers)
        data = res.json()

        return data["data"]["IDX_I"][str(security_id)]["last_price"]

    except Exception as e:
        return "-"# ------------------ OPTION CHAIN ------------------
def get_option_chain(symbol):
    try:
        import requests

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

        return table, data

    except Exception as e:
        return [html.Tr([html.Td("Error loading data")])], {"error": str(e)}    except Exception as e:
        return [html.Tr([html.Td("Error")])], {"error": str(e)}# ------------------ CALLBACK ------------------
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
