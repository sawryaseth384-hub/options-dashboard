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
    ),

    # ===== PRO ANALYTICS PANEL =====
    html.H3("PRO ANALYTICS"),
    html.Div(id="market-status", style={
        "color": "yellow",
        "fontSize": "18px",
        "whiteSpace": "pre-line"
    }),
    html.Div(id="ai-signal", style={
        "color": "cyan",
        "fontSize": "18px"
    })
])

# =========================
# CALLBACK
# =========================
@app.callback(
    [
        Output("ltp", "children"),
        Output("option-table", "children"),
        Output("raw-json", "children"),
        Output("market-status", "children"),
        Output("ai-signal", "children")
    ],
    [
        Input("interval", "n_intervals"),
        Input("symbol", "value")
    ]
)
def update_dashboard(n, symbol):
    raw_output = ""
    market_status = "Loading..."
    ai_signal = "Analyzing..."

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

        # =========================
        # PRO ANALYTICS
        # =========================
        total_ce_oi = 0
        total_pe_oi = 0

        for r in rows:
            total_ce_oi += r.get("ce", {}).get("oi", 0)
            total_pe_oi += r.get("pe", {}).get("oi", 0)

        pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi else 0

        # Trend Detection
        if pcr > 1.3:
            trend = "BULLISH 🟢"
        elif pcr < 0.7:
            trend = "BEARISH 🔴"
        else:
            trend = "SIDEWAYS 🟡"

        atm = min(
            [r.get("strikePrice", 0) for r in rows if r.get("strikePrice")],
            key=lambda x: abs(x - (underlying if isinstance(underlying, (int, float)) else 0)),
            default=0
        ) if rows else 0

        market_status = f"""Spot: {ltp_value}
ATM: {atm}
PCR: {pcr}
Trend: {trend}
"""

        # =========================
        # AI STRIKE SELECTION
        # =========================
        best_call = None
        best_put = None
        max_call_score = 0
        max_put_score = 0

        for r in rows:
            ce = r.get("ce", {})
            pe = r.get("pe", {})

            call_score = ce.get("oi_change", 0) + ce.get("volume", 0)
            put_score = pe.get("oi_change", 0) + pe.get("volume", 0)

            if call_score > max_call_score:
                max_call_score = call_score
                best_call = r.get("strikePrice")

            if put_score > max_put_score:
                max_put_score = put_score
                best_put = r.get("strikePrice")

        # Final Signal
        if pcr > 1:
            ai_signal = f"BUY CALL → {best_call} CE 🚀" if best_call else "No Data"
        elif pcr < 1:
            ai_signal = f"BUY PUT → {best_put} PE 🔻" if best_put else "No Data"
        else:
            ai_signal = "NO CLEAR TRADE ❌"

        return ltp_value, table, raw_output, market_status, ai_signal

    except Exception as e:
        raw_output += "\n\nERROR:\n" + str(e)
        market_status = "Error loading analytics"
        ai_signal = "Error generating signal"
        return "Error loading data", [html.Tr([html.Td("Error")])], raw_output, market_status, ai_signal


# =========================
# RUN (RAILWAY SAFE)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port)
