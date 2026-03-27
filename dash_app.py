import os
import json
import time
from datetime import datetime
import math
import requests
import pandas as pd
import plotly.graph_objs as go
from dash import Dash, html, dcc, dash_table, Input, Output, State, no_update
import dash_bootstrap_components as dbc

# ---------- Environment ----------
CLIENT_ID = os.getenv("CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
PORT = int(os.environ.get("PORT", 5000))
VERBOSE_LOG = os.getenv("VERBOSE_LOG", "0") == "1"

headers = {
    "access-token": DHAN_ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
}

# ---------- Constants ----------
LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
EXPIRY_URL = "https://api.dhan.co/v2/optionChain/expiryList"
OPTION_CHAIN_URL = "https://api.dhan.co/v2/optionChain"
UNDERLYINGS = {"NIFTY": {"id": 13, "segment": "IDX_I"}}
MAX_POINTS = 200
REQUEST_TIMEOUT = 3
EXPIRY_TTL_SECONDS = 300  # cache 5 minutes
REFRESH_MS_BASE = 1000  # 1s
OPTION_REFRESH_EVERY = 6  # every ~6s at base rate
BACKOFF_MAX = 5000  # ms (5s)

# ---------- Session (connection pooling) ----------
session = requests.Session()

# ---------- Cache ----------
expiry_cache = {}  # {symbol: {"code": ..., "ts": ...}}
option_cache = {}  # {symbol: {"rows": [...], "ts": ..., "code": ...}}

# ---------- Helpers ----------
def mask_token(token: str) -> str:
    if not token:
        return "MISSING"
    if len(token) <= 6:
        return token[0] + "***"
    return token[:4] + "***" + token[-2:]

def log_debug(url, payload, response=None, error=None, elapsed=None):
    if not VERBOSE_LOG and error is None:
        return
    status = response.status_code if response else "NO_RESPONSE"
    body_preview = ""
    if response:
        try:
            body_preview = response.text[:300]
        except Exception:
            body_preview = "<unreadable>"
    if error:
        body_preview = f"ERROR: {error}"
    print("\n--- DHAN DEBUG ---")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload)}")
    print(f"Status Code: {status}")
    if elapsed is not None:
        print(f"Elapsed: {elapsed:.3f}s")
    print(f"Response (first 300 chars): {body_preview}")
    print("------------------\n")

def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return None

def post_api(url, payload):
    start = time.perf_counter()
    try:
        resp = session.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        elapsed = time.perf_counter() - start
        if resp.status_code == 401:
            log_debug(url, payload, response=resp, elapsed=elapsed)
            return None, "Token invalid or expired"
        data = safe_json(resp)
        if data is None:
            log_debug(url, payload, response=resp, elapsed=elapsed)
            return None, f"Non-JSON response: {resp.text[:200]}"
        log_debug(url, payload, response=resp, elapsed=elapsed)
        return data, None
    except Exception as e:
        elapsed = time.perf_counter() - start
        log_debug(url, payload, response=None, error=str(e), elapsed=elapsed)
        return None, f"Request error: {e}"

def fetch_ltp(underlying_id: int):
    payload = {"NSE_INDEX": [underlying_id]}
    data, err = post_api(LTP_URL, payload)
    if err:
        return None, err
    ltp = None
    try:
        items = data.get("data") or data.get("ltp") or data
        if isinstance(items, list) and items:
            cand = items[0]
            ltp = cand.get("ltp") or cand.get("LTP") or cand.get("lastPrice") or cand.get("LastPrice")
        elif isinstance(items, dict):
            ltp = items.get("ltp") or items.get("LTP") or items.get("lastPrice") or items.get("LastPrice")
    except Exception:
        pass
    if ltp is None:
        return None, "LTP data missing in response"
    return float(ltp), None

def fetch_expiry_code(symbol: str, underlying_id: int, segment: str):
    now = time.time()
    cached = expiry_cache.get(symbol)
    if cached and now - cached["ts"] < EXPIRY_TTL_SECONDS:
        return cached["code"], None

    payload = {"UnderlyingScrip": underlying_id, "UnderlyingSeg": segment}
    data, err = post_api(EXPIRY_URL, payload)
    if err:
        return None, err
    expiry_list = data.get("data") or data.get("expiryList") or data.get("expiries") or data
    code = None
    if isinstance(expiry_list, list) and expiry_list:
        first = expiry_list[0]
        if isinstance(first, dict):
            code = first.get("expiryCode") or first.get("ExpiryCode") or first.get("code") or first.get("Code")
        elif isinstance(first, (str, int)):
            code = first
    if code is None:
        return None, "Expiry code missing in response"
    expiry_cache[symbol] = {"code": code, "ts": now}
    return code, None

def parse_option_chain(json_data):
    rows = []
    options = json_data.get("data") or json_data.get("options") or json_data.get("optionChain") or []
    if not isinstance(options, list):
        return rows
    for item in options:
        strike = item.get("strikePrice") or item.get("StrikePrice") or item.get("strike")
        ce = pe = None
        if isinstance(item.get("callOption"), dict):
            ce = item["callOption"].get("ltp") or item["callOption"].get("LTP")
        if isinstance(item.get("putOption"), dict):
            pe = item["putOption"].get("ltp") or item["putOption"].get("LTP")
        if isinstance(item.get("CE"), dict):
            ce = ce or item["CE"].get("ltp") or item["CE"].get("LTP")
        if isinstance(item.get("PE"), dict):
            pe = pe or item["PE"].get("ltp") or item["PE"].get("LTP")
        if strike is not None:
            rows.append({"Strike": strike, "CE LTP": ce, "PE LTP": pe})
    return rows

def fetch_option_chain(symbol: str, underlying_id: int, segment: str, expiry_code):
    now = time.time()
    cached = option_cache.get(symbol)
    if cached and cached.get("code") == expiry_code and now - cached["ts"] < OPTION_REFRESH_EVERY:
        return cached["rows"], None

    payload = {
        "UnderlyingScrip": underlying_id,
        "UnderlyingSeg": segment,
        "ExpiryCode": expiry_code,
    }
    data, err = post_api(OPTION_CHAIN_URL, payload)
    if err:
        return None, err
    rows = parse_option_chain(data)
    if not rows:
        return None, "Option chain data missing in response"
    option_cache[symbol] = {"rows": rows, "ts": now, "code": expiry_code}
    return rows, None

def build_price_figure(history):
    if not history:
        return go.Figure(
            layout=go.Layout(
                template="plotly_dark",
                title="Price History (Waiting for data...)",
                xaxis_title="Time",
                yaxis_title="LTP",
            )
        )
    df = pd.DataFrame(history)
    fig = go.Figure(
        data=[go.Scatter(x=df["time"], y=df["ltp"], mode="lines+markers", name="LTP")],
        layout=go.Layout(
            template="plotly_dark",
            title="Live LTP (last 200 points)",
            xaxis_title="Time",
            yaxis_title="LTP",
        ),
    )
    return fig

def calc_signal(history, option_rows):
    if not history or len(history) < 5:
        return "NO TRADE", "secondary"
    last_prices = [p["ltp"] for p in history[-10:]]
    momentum = last_prices[-1] - last_prices[0]
    slope = momentum / max(len(last_prices) - 1, 1)
    ce_strength = max([r["CE LTP"] for r in option_rows if r.get("CE LTP") is not None], default=0)
    pe_strength = max([r["PE LTP"] for r in option_rows if r.get("PE LTP") is not None], default=0)
    if slope > 0 and ce_strength >= pe_strength:
        return "BUY CALL", "success"
    if slope < 0 and pe_strength >= ce_strength:
        return "BUY PUT", "danger"
    return "NO TRADE", "secondary"

def find_atm_strike(ltp, option_rows):
    if ltp is None or not option_rows:
        return None
    strikes = [r["Strike"] for r in option_rows if r.get("Strike") is not None]
    if not strikes:
        return None
    return min(strikes, key=lambda x: abs(x - ltp))

def find_best_strikes(option_rows):
    if not option_rows:
        return None, None
    best_ce = max(option_rows, key=lambda r: r.get("CE LTP") or -math.inf)
    best_pe = max(option_rows, key=lambda r: r.get("PE LTP") or -math.inf)
    return best_ce.get("Strike"), best_pe.get("Strike")

def style_option_table(atm, best_ce, best_pe):
    styles = []
    if atm is not None:
        styles.append({
            "if": {"filter_query": f'{{Strike}} = {atm}'},
            "backgroundColor": "#333333",
            "fontWeight": "bold",
        })
    if best_ce is not None:
        styles.append({
            "if": {"filter_query": f'{{Strike}} = {best_ce}'},
            "color": "#2ecc71",
        })
    if best_pe is not None:
        styles.append({
            "if": {"filter_query": f'{{Strike}} = {best_pe}'},
            "color": "#e74c3c",
        })
    return styles

# ---------- Dash App ----------
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server  # required for Replit preview

app.layout = dbc.Container(
    [
        dcc.Store(id="price-store", data=[]),
        dcc.Store(id="option-store", data=[]),
        dcc.Store(id="backoff-store", data={"interval": REFRESH_MS_BASE}),
        html.H2("AI Trading Dashboard (Dhan)", className="my-3"),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Alert("NO TRADE", id="signal-banner", color="secondary", className="text-center mb-3"),
                    md=3,
                ),
                dbc.Col(
                    dbc.Alert("Waiting for data...", id="status-banner", color="secondary", className="text-center mb-3"),
                    md=9,
                ),
            ],
            className="mb-2",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Symbol"),
                        dcc.Dropdown(
                            id="symbol-dropdown",
                            options=[{"label": "NIFTY 50", "value": "NIFTY"}],
                            value="NIFTY",
                            clearable=False,
                        ),
                    ],
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Latest Traded Price"),
                                html.H2(id="ltp-card-value", children="--"),
                            ]
                        ),
                        className="mt-2",
                    ),
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(id="debug-panel"),
                        className="mt-2",
                    ),
                    md=6,
                ),
            ],
            className="mb-3",
        ),
        dbc.Row([dbc.Col(dcc.Graph(id="ltp-graph"), md=12)], className="mb-3"),
        dbc.Row(
            [
                dbc.Col(
                    dash_table.DataTable(
                        id="option-chain-table",
                        columns=[
                            {"name": "Strike", "id": "Strike"},
                            {"name": "CE LTP", "id": "CE LTP"},
                            {"name": "PE LTP", "id": "PE LTP"},
                        ],
                        data=[],
                        style_table={"overflowX": "auto"},
                        style_header={"backgroundColor": "#1f1f1f", "color": "white"},
                        style_cell={"backgroundColor": "#2b2b2b", "color": "white"},
                        page_size=20,
                    ),
                    md=12,
                )
            ]
        ),
        dcc.Interval(id="update-interval", interval=REFRESH_MS_BASE, n_intervals=0),
    ],
    fluid=True,
)

# ---------- Callbacks ----------
@app.callback(
    [
        Output("price-store", "data"),
        Output("option-store", "data"),
        Output("ltp-card-value", "children"),
        Output("status-banner", "children"),
        Output("status-banner", "color"),
        Output("signal-banner", "children"),
        Output("signal-banner", "color"),
        Output("ltp-graph", "figure"),
        Output("option-chain-table", "data"),
        Output("option-chain-table", "style_data_conditional"),
        Output("debug-panel", "children"),
        Output("update-interval", "interval"),
        Output("backoff-store", "data"),
    ],
    [Input("update-interval", "n_intervals"), Input("symbol-dropdown", "value")],
    [State("price-store", "data"), State("option-store", "data"), State("backoff-store", "data")],
)
def refresh_data(n, symbol, history, option_rows, backoff_state):
    history = history or []
    option_rows = option_rows or []
    backoff_ms = backoff_state.get("interval", REFRESH_MS_BASE) if backoff_state else REFRESH_MS_BASE
    status_msgs = []
    status_color = "secondary"
    ltp_val = history[-1]["ltp"] if history else None
    expiry_code = None
    interval_ms = REFRESH_MS_BASE  # default back to base each cycle unless error
    api_error = False

    if not CLIENT_ID or not DHAN_ACCESS_TOKEN:
        msg = "Missing CLIENT_ID or DHAN_ACCESS_TOKEN environment variables."
        return history, option_rows, ltp_val or "--", msg, "danger", "NO TRADE", "secondary", build_price_figure(history), option_rows, [], build_debug_panel(msg, ltp_val, None, len(option_rows)), backoff_ms, {"interval": backoff_ms}

    underlying = UNDERLYINGS.get(symbol)
    if not underlying:
        msg = f"Unsupported symbol: {symbol}"
        return history, option_rows, ltp_val or "--", msg, "danger", "NO TRADE", "secondary", build_price_figure(history), option_rows, [], build_debug_panel(msg, ltp_val, None, len(option_rows)), backoff_ms, {"interval": backoff_ms}

    # LTP fetch (every tick)
    ltp, err = fetch_ltp(underlying["id"])
    if err:
        status_msgs.append(f"LTP: {err}")
        api_error = True
    else:
        timestamp = datetime.now().strftime("%H:%M:%S")
        history.append({"time": timestamp, "ltp": ltp})
        history = history[-MAX_POINTS:]
        status_msgs.append("LTP fetched")
        status_color = "success"
        ltp_val = ltp

    # Option chain fetch throttled
    do_option = n % OPTION_REFRESH_EVERY == 0
    if do_option and ltp_val is not None:
        expiry_code, expiry_err = fetch_expiry_code(symbol, underlying["id"], underlying["segment"])
        if expiry_err:
            status_msgs.append(f"Expiry: {expiry_err}")
            api_error = True
        else:
            oc_rows, oc_err = fetch_option_chain(symbol, underlying["id"], underlying["segment"], expiry_code)
            if oc_err:
                status_msgs.append(f"Option Chain: {oc_err}")
                api_error = True
            else:
                option_rows = oc_rows
                status_msgs.append("Option Chain fetched")
                if status_color != "danger":
                    status_color = "success"

    if not status_msgs:
        status_msgs.append("Waiting for data...")

    # Backoff logic
    if api_error:
        interval_ms = min(backoff_ms * 2, BACKOFF_MAX)
        status_msgs.append(f"BACKOFF {interval_ms}ms")
        status_state = "ERROR"
    elif backoff_ms > REFRESH_MS_BASE:
        interval_ms = REFRESH_MS_BASE
        status_msgs.append("LIVE")
        status_state = "LIVE"
    else:
        interval_ms = REFRESH_MS_BASE
        status_state = "LIVE"

    status_text = " | ".join(status_msgs)
    ltp_display = f"{ltp_val:.2f}" if isinstance(ltp_val, (int, float)) else (ltp_val or "--")

    # Signals & strikes
    signal_text, signal_color = calc_signal(history, option_rows)
    atm_strike = find_atm_strike(ltp_val, option_rows)
    best_ce, best_pe = find_best_strikes(option_rows)
    table_styles = style_option_table(atm_strike, best_ce, best_pe)

    debug_panel = build_debug_panel(
        status_text,
        last_ltp=ltp_display,
        expiry_code=expiry_code,
        option_rows=len(option_rows),
        atm=atm_strike,
        best_ce=best_ce,
        best_pe=best_pe,
        status_state=status_state,
    )

    return (
        history,
        option_rows,
        ltp_display,
        status_text,
        status_color if not api_error else "warning",
        signal_text,
        signal_color,
        build_price_figure(history),
        option_rows if do_option or option_rows else option_rows,
        table_styles,
        debug_panel,
        interval_ms,
        {"interval": interval_ms},
    )

def build_debug_panel(status, last_ltp=None, expiry_code=None, option_rows=0, atm=None, best_ce=None, best_pe=None, status_state="LIVE"):
    return html.Div(
        [
            html.Div(f"Status: {status} ({status_state})"),
            html.Div(f"CLIENT_ID: {mask_token(CLIENT_ID)}"),
            html.Div(f"ACCESS_TOKEN: {mask_token(DHAN_ACCESS_TOKEN)}"),
            html.Div(f"Last LTP: {last_ltp or 'Waiting for data...'}"),
            html.Div(f"Expiry Code: {expiry_code or 'Waiting for data...'}"),
            html.Div(f"ATM Strike: {atm or '--'}"),
            html.Div(f"Best CE Strike: {best_ce or '--'}"),
            html.Div(f"Best PE Strike: {best_pe or '--'}"),
            html.Div(f"Option Rows: {option_rows}"),
        ]
    )

# ---------- Entrypoint ----------
if __name__ == "__main__":
    print(f"Server starting on port {PORT}...")
    app.run(host="0.0.0.0", port=PORT, debug=False)
