import os, time, math, requests
from dash import Dash, html, dcc, no_update, Input, Output, State

# --- Import your existing Dhan API helpers (adjust module/function names as needed) ---
# These MUST be the real functions you already use; do not swap with dummy endpoints.
from dhan_api import fetch_ltp, fetch_option_chain, fetch_expiry  # <-- change to your actual module

# ----------------- Config -----------------
LTP_INTERVAL_MS = 1000           # 1s LTP
OC_INTERVAL_MS  = 8000           # 6–10s; set 8s
OC_CACHE_TTL    = 15             # seconds
BACKOFF_CAP_MS  = 30000          # max 30s backoff
API_TIMEOUT     = 4              # seconds
DARK_BG         = "#0b0f19"
PANEL_BG        = "#131a2a"

# ----------------- Caches & state -----------------
oc_cache = {"data": None, "expires": 0}
expiry_cache = {"data": None, "expires": 0}

def capped_backoff(prev_ms, failed):
    if not failed:
        return LTP_INTERVAL_MS
    new_ms = min(prev_ms * 2, BACKOFF_CAP_MS)
    return new_ms

# ----------------- Wrappers around your existing calls -----------------
def get_ltp():
    # Your existing function should return a dict with at least {"price": float, "timestamp": ...}
    return fetch_ltp(timeout=API_TIMEOUT)

def get_option_chain():
    # Your existing function should return (data, expiry_str) or similar structure you already use
    return fetch_option_chain(timeout=API_TIMEOUT)

def get_expiry_list():
    return fetch_expiry(timeout=API_TIMEOUT)

# ----------------- Dash App -----------------
external_stylesheets = [
    "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
    "https://cdnjs.cloudflare.com/ajax/libs/bootswatch/5.3.3/darkly/bootstrap.min.css",
]
app = Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
server = app.server
app.title = "Trading Dashboard"

app.layout = html.Div(
    style={"backgroundColor": DARK_BG, "color": "#e4e8f0", "minHeight": "100vh", "padding": "12px"},
    children=[
        html.Div(
            style={"background": PANEL_BG, "padding": "10px", "borderRadius": "8px", "marginBottom": "12px"},
            children=[
                html.H4("Status", className="mb-2"),
                html.Div(id="status-banner", className="badge bg-success", style={"fontSize": "1rem"}),
                html.Div(id="last-ltp", className="mt-2"),
                html.Div(id="last-expiry", className="mt-1"),
                html.Div(id="last-error", className="text-danger mt-2", style={"whiteSpace": "pre-wrap"}),
            ],
        ),
        dcc.Graph(id="ltp-graph", style={"height": "340px", "background": PANEL_BG}),
        dcc.Store(id="oc-store"),
        dcc.Interval(id="ltp-timer", interval=LTP_INTERVAL_MS, n_intervals=0),
        dcc.Interval(id="oc-timer", interval=OC_INTERVAL_MS, n_intervals=0),
    ],
)

# ----------------- Callbacks -----------------
@app.callback(
    Output("ltp-graph", "figure"),
    Output("status-banner", "children"),
    Output("status-banner", "className"),
    Output("last-ltp", "children"),
    Output("last-error", "children"),
    Output("ltp-timer", "interval"),
    Input("ltp-timer", "n_intervals"),
    State("ltp-timer", "interval"),
    prevent_initial_call=False,
)
def update_ltp(_n, current_interval):
    try:
        ltp = get_ltp()  # keep your existing logic
        price = ltp.get("price", math.nan)
        ts = ltp.get("timestamp", time.time())
        fig = {
            "data": [
                {
                    "x": [ts],
                    "y": [price],
                    "mode": "lines+markers",
                    "marker": {"color": "#5bc0de"},
                    "name": "LTP",
                }
            ],
            "layout": {
                "margin": {"l": 40, "r": 10, "t": 20, "b": 40},
                "paper_bgcolor": PANEL_BG,
                "plot_bgcolor": PANEL_BG,
                "font": {"color": "#e4e8f0"},
                "height": 330,
            },
        }
        return (
            fig,
            "LIVE",
            "badge bg-success",
            f"Last LTP: {price}",
            "",
            LTP_INTERVAL_MS,
        )
    except Exception as e:
        # backoff on failure
        new_interval = capped_backoff(current_interval, failed=True)
        return (
            no_update,
            "BACKOFF",
            "badge bg-warning text-dark",
            no_update,
            f"LTP error: {type(e).__name__}: {e}",
            new_interval,
        )

@app.callback(
    Output("oc-store", "data"),
    Output("last-expiry", "children"),
    Output("last-error", "children", allow_duplicate=True),
    Output("oc-timer", "interval"),
    Input("oc-timer", "n_intervals"),
    State("oc-timer", "interval"),
    prevent_initial_call=False,
)
def refresh_option_chain(_n, current_interval):
    now = time.time()
    # Cache check
    if oc_cache["data"] and now < oc_cache["expires"]:
        return oc_cache["data"], no_update, no_update, current_interval

    try:
        oc_data, expiry = get_option_chain()  # keep your data shape
        oc_cache["data"] = oc_data
        oc_cache["expires"] = now + OC_CACHE_TTL
        expiry_text = f"Expiry: {expiry}" if expiry else "Expiry: -"
        return oc_data, expiry_text, "", OC_INTERVAL_MS
    except Exception as e:
        new_interval = capped_backoff(current_interval, failed=True)
        return no_update, no_update, f"OC error: {type(e).__name__}: {e}", new_interval)

# ----------------- Entry point -----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run_server(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,   # single process; prevents preview crashes
    )
