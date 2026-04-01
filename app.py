import os
import requests
from datetime import datetime, timedelta
from dash import Dash, html, dcc, Input, Output
from dash.dash_table import DataTable

# =========================
# CONFIGURATION
# =========================
BASE_URL = "https://api.dhan.co/v2"

SYMBOL_MAP = {
    "NIFTY": 13,
    "BANKNIFTY": 25,
    "FINNIFTY": 27
}

# Get from environment
ACCESS_TOKEN = os.getenv("DHAN_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")

# Validate on startup
if not ACCESS_TOKEN:
    print("❌ ERROR: DHAN_TOKEN environment variable not set!")
if not CLIENT_ID:
    print("❌ ERROR: CLIENT_ID environment variable not set!")

# =========================
# API FUNCTIONS
# =========================
def get_headers():
    """Return headers for API requests"""
    if not ACCESS_TOKEN or not CLIENT_ID:
        raise ValueError("Missing ACCESS_TOKEN or CLIENT_ID")
    
    return {
        "access-token": ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }

def test_token_validity():
    """Test if current token is valid"""
    try:
        url = "https://api.dhan.co/v2/accounts/profile"
        headers = {
            "access-token": ACCESS_TOKEN,
            "client-id": CLIENT_ID
        }
        res = requests.get(url, headers=headers, timeout=10)
        return res.status_code == 200
    except:
        return False

def get_expiry_list(symbol):
    """Fetch available expiry dates"""
    if not test_token_validity():
        return [], "❌ Token expired! Please regenerate token."
    
    try:
        url = f"{BASE_URL}/optionchain/expirylist"
        payload = {
            "UnderlyingScrip": SYMBOL_MAP[symbol],
            "UnderlyingSeg": "IDX_I"
        }
        
        res = requests.post(url, json=payload, headers=get_headers(), timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            expiries = data.get("data", [])
            return expiries, ""
        elif res.status_code == 401:
            return [], "❌ Token expired! Please regenerate your access token."
        elif res.status_code == 404:
            return [], "❌ API endpoint not found. Check your URL."
        else:
            return [], f"❌ Error {res.status_code}: {res.text[:100]}"
            
    except Exception as e:
        return [], f"❌ Exception: {str(e)}"

def get_option_chain(symbol, expiry):
    """Fetch option chain data"""
    if not test_token_validity():
        return [], "❌ Token expired! Please regenerate token."
    
    try:
        url = f"{BASE_URL}/optionchain"
        payload = {
            "UnderlyingScrip": SYMBOL_MAP[symbol],
            "UnderlyingSeg": "IDX_I",
            "Expiry": expiry
        }
        
        res = requests.post(url, json=payload, headers=get_headers(), timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            oc_data = data.get("data", {})
            strikes_dict = oc_data.get("oc", {})
            
            rows = []
            strikes = sorted([int(k) for k in strikes_dict.keys()])
            
            for strike in strikes[:20]:
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
                    "Put IV": pe.get("implied_volatility", "-")
                })
            
            status_msg = f"✅ Loaded {len(rows)} strikes | Underlying: {oc_data.get('last_price', '-')}"
            return rows, status_msg
            
        elif res.status_code == 401:
            return [], "❌ Token expired! Generate new token from Dhan app."
        elif res.status_code == 404:
            return [], f"❌ No data for {expiry}. Try different expiry date."
        elif res.status_code == 400:
            return [], "❌ Invalid request. Check symbol or expiry format."
        else:
            return [], f"❌ Error {res.status_code}: {res.text[:100]}"
            
    except requests.exceptions.Timeout:
        return [], "❌ Request timeout. Check your internet."
    except Exception as e:
        return [], f"❌ Exception: {str(e)}"

# =========================
# DASH APP
# =========================
app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H2("📊 Dhan Option Chain Dashboard", style={"textAlign": "center"}),
    
    html.Div([
        html.Div([
            html.Label("Select Index:"),
            dcc.Dropdown(
                id="symbol",
                options=[{"label": k, "value": k} for k in SYMBOL_MAP.keys()],
                value="NIFTY",
                clearable=False
            )
        ], style={"width": "30%", "display": "inline-block", "marginRight": "20px"}),
        
        html.Div([
            html.Label("Select Expiry:"),
            dcc.Dropdown(id="expiry", clearable=False)
        ], style={"width": "40%", "display": "inline-block"})
    ], style={"margin": "20px"}),
    
    html.Div(id="status", style={"color": "red", "margin": "20px", "fontWeight": "bold"}),
    
    html.Div(id="token-status", style={"color": "orange", "margin": "20px"}),
    
    DataTable(
        id="table",
        columns=[
            {"name": "Strike", "id": "Strike"},
            {"name": "Call OI", "id": "Call OI"},
            {"name": "Put OI", "id": "Put OI"},
            {"name": "Call LTP", "id": "Call LTP"},
            {"name": "Put LTP", "id": "Put LTP"},
            {"name": "Call IV (%)", "id": "Call IV"},
            {"name": "Put IV (%)", "id": "Put IV"}
        ],
        style_cell={"textAlign": "center", "padding": "10px"},
        style_header={"backgroundColor": "#2c3e50", "color": "white", "fontWeight": "bold"},
        style_data={"backgroundColor": "#ecf0f1"},
        page_size=15
    ),
    
    dcc.Interval(id="refresh", interval=10000)  # Refresh every 10 seconds
])

# =========================
# CALLBACKS
# =========================
@app.callback(
    Output("token-status", "children"),
    Input("refresh", "n_intervals")
)
def check_token(n):
    if not ACCESS_TOKEN or not CLIENT_ID:
        return "⚠️ Missing DHAN_TOKEN or CLIENT_ID environment variables!"
    
    if test_token_validity():
        return "✅ Token valid"
    else:
        return "⚠️ Token expired! Please generate new token from Dhan app."

@app.callback(
    Output("expiry", "options"),
    Output("expiry", "value"),
    Input("symbol", "value")
)
def load_expiry(symbol):
    expiries, error = get_expiry_list(symbol)
    
    if error:
        print(f"Expiry error: {error}")
        return [], None
    
    opts = [{"label": e, "value": e} for e in expiries]
    return opts, expiries[0] if expiries else None

@app.callback(
    Output("table", "data"),
    Output("status", "children"),
    Input("symbol", "value"),
    Input("expiry", "value"),
    Input("refresh", "n_intervals")
)
def update_table(symbol, expiry, n):
    if not ACCESS_TOKEN or not CLIENT_ID:
        return [], "❌ Missing environment variables!"
    
    if not expiry:
        return [], "⏳ Loading expiries..."
    
    data, status = get_option_chain(symbol, expiry)
    return data, status


