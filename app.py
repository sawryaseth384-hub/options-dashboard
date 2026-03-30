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
# ENV - Set these before running
# =========================
ACCESS_TOKEN = os.getenv("DHAN_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")

# =========================
# API FUNCTIONS (Fixed)
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
        print("EXPIRY FULL:", res.status_code, res.text)

        if res.status_code != 200:
            return []

        data = res.json()

        # 🔥 HANDLE ALL POSSIBLE STRUCTURES
        expiry_data = data.get("data", {})

        if isinstance(expiry_data, list):
            return expiry_data

        if isinstance(expiry_data, dict):
            return expiry_data.get("expiryDates", [])

        return []

    except Exception as e:
        print("Expiry Error:", e)
        return []        data = res.json()
        # Dhan returns expiry list in 'data' array
        return data.get("data", [])

    except Exception as e:
        print("Expiry Error:", e)
        return []

def get_option_chain(symbol, expiry):
    """Fetch option chain with proper parsing"""
    try:
        url = f"{BASE_URL}/optionchain"
        payload = {
            "UnderlyingScrip": SYMBOL_MAP[symbol],
            "UnderlyingSeg": "IDX_I",
            "Expiry": expiry
        }

        res = requests.post(url, json=payload, headers=get_headers())
        print("CHAIN Response:", res.status_code)

        if res.status_code != 200:
            return [], f"API Error {res.status_code}: {res.text}"

        data = res.json()
        
        # Dhan's response structure:
        # {
        #   "data": {
        #     "last_price": 23500.50,
        #     "oc": {
        #       "23500": { "ce": {...}, "pe": {...} },
        #       "23600": { "ce": {...}, "pe": {...} }
        #     }
        #   }
        # }
        
        oc_data = data.get("data", {})
        strikes_dict = oc_data.get("oc", {})
        
        rows = []
        # Convert strikes to sorted list of integers
        strikes = sorted([int(k) for k in strikes_dict.keys()])
        
        for strike in strikes[:20]:  # Limit to 20 strikes for performance
            strike_str = str(strike)
            contracts = strikes_dict.get(strike_str, {})
            
            ce = contracts.get("ce", {})
            pe = contracts.get("pe", {})
            
            rows.append({
                "Strike": strike,
                "Call OI": ce.get("oi", "-"),
                "Put OI": pe.get("oi", "-"),
                "Call LTP": ce.get("last_price", "-"),
                "Put LTP": pe.get("last_price", "-"),
                "Call IV": ce.get("implied_volatility", "-"),
                "Put IV": pe.get("implied_volatility", "-"),
                "Underlying LTP": oc_data.get("last_price", "-")
            })
        
        return rows, f"Underlying: {oc_data.get('last_price', '-')} | Strikes: {len(strikes)}"

    except Exception as e:
        return [], str(e)

# =========================
# DASH APP
# =========================
app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H2("Dhan Option Chain Dashboard", style={"textAlign": "center"}),
    
    html.Div([
        html.Label("Select Index:"),
        dcc.Dropdown(
            id="symbol",
            options=[{"label": k, "value": k} for k in SYMBOL_MAP.keys()],
            value="NIFTY",
            style={"width": "50%"}
        ),
    ], style={"margin": "20px"}),
    
    html.Div([
        html.Label("Select Expiry:"),
        dcc.Dropdown(id="expiry", style={"width": "50%"}),
    ], style={"margin": "20px"}),
    
    html.Div(id="status", style={"color": "red", "margin": "20px"}),
    
    DataTable(
        id="table",
        columns=[
            {"name": "Strike", "id": "Strike"},
            {"name": "Call OI", "id": "Call OI"},
            {"name": "Put OI", "id": "Put OI"},
            {"name": "Call LTP", "id": "Call LTP"},
            {"name": "Put LTP", "id": "Put LTP"},
            {"name": "Call IV", "id": "Call IV"},
            {"name": "Put IV", "id": "Put IV"},
            {"name": "Underlying LTP", "id": "Underlying LTP"},
        ],
        style_cell={"textAlign": "center"},
        style_header={"backgroundColor": "lightgray", "fontWeight": "bold"},
        page_size=20
    ),
    
    dcc.Interval(id="refresh", interval=5000)  # Refresh every 5 seconds
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
    if not ACCESS_TOKEN or not CLIENT_ID:
        return [], None
    
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
    # Validation
    if not ACCESS_TOKEN or not CLIENT_ID:
        return [], "❌ Missing DHAN_TOKEN or CLIENT_ID environment variables"
    
    if not expiry:
        return [], "⏳ Loading expiries..."
    
    if symbol not in SYMBOL_MAP:
        return [], f"❌ Invalid symbol: {symbol}"
    
    # Fetch data
    data, status = get_option_chain(symbol, expiry)
    
    if not data and "Error" not in status:
        status = "⚠️ No data received. Check token validity."
    
    return data, status

# =========================
# RUN
# =========================
if __name__ == "__main__":
    print("=" * 50)
    print("Dhan Option Chain Dashboard")
    print("=" * 50)
    print(f"Client ID: {CLIENT_ID[:4] + '****' if CLIENT_ID else 'NOT SET'}")
    print(f"Access Token: {'SET' if ACCESS_TOKEN else 'NOT SET'}")
    print("=" * 50)
    
    port = int(os.getenv("PORT", 8080))
    app.run_server(host="0.0.0.0", port=port, debug=False)
