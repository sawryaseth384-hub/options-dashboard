"""
Production-ready Dash AI Trading Dashboard
Dhan API integration · EMA + VWAP + Momentum · PCR · Smart Strike · Trade Plan
Railway deployment ready (gunicorn + Procfile)
"""

import os
import time
import threading
import logging
from datetime import datetime, timedelta
from functools import wraps

import requests
import pandas as pd
import plotly.graph_objs as go
from dash import Dash, html, dcc, dash_table, Input, Output, State, no_update
import dash_bootstrap_components as dbc

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment / Config
# ---------------------------------------------------------------------------
CLIENT_ID = os.environ.get("CLIENT_ID", "")
DHAN_ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN", "")
PORT = int(os.environ.get("PORT", 8050))

REQUEST_TIMEOUT = 5  # seconds
CACHE_TTL = 15       # seconds for LTP / option-chain cache

# ---------------------------------------------------------------------------
# Dhan API constants
# ---------------------------------------------------------------------------
BASE_URL = "https://api.dhan.co/v2"
LTP_URL = f"{BASE_URL}/marketfeed/ltp"
EXPIRY_URL = f"{BASE_URL}/optionChain/expiryList"
OC_URL = f"{BASE_URL}/optionChain"

UNDERLYINGS = {
    "NIFTY": {"id": 13, "segment": "IDX_I"},
    "BANKNIFTY": {"id": 25, "segment": "IDX_I"},
}

# ---------------------------------------------------------------------------
# Simple thread-safe TTL cache
# ---------------------------------------------------------------------------
_cache: dict = {}
_cache_lock = threading.Lock()


def ttl_cache(key: str, fn, ttl: int = CACHE_TTL):
    """Return cached value if fresh, else call fn() and cache result."""
    with _cache_lock:
        entry = _cache.get(key)
        if entry and (time.time() - entry["ts"]) < ttl:
            return entry["val"], None
    try:
        val = fn()
        with _cache_lock:
            _cache[key] = {"val": val, "ts": time.time()}
        return val, None
    except (RuntimeError, ValueError, TypeError, requests.exceptions.RequestException) as exc:
        _logger.error("Cache fn error for key=%s: %s", key, exc)
        return None, str(exc)


# ---------------------------------------------------------------------------
# Dhan API helpers
# ---------------------------------------------------------------------------
def _headers() -> dict:
    return {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json",
    }


def _post(url: str, payload: dict):
    """POST with timeout + JSON parsing; returns (data_dict, error_str)."""
    if not DHAN_ACCESS_TOKEN or not CLIENT_ID:
        return None, "API credentials not configured (CLIENT_ID / DHAN_ACCESS_TOKEN missing)"
    try:
        resp = requests.post(
            url, headers=_headers(), json=payload, timeout=REQUEST_TIMEOUT
        )
        if resp.status_code == 401:
            return None, "Unauthorized – check DHAN_ACCESS_TOKEN"
        if resp.status_code == 429:
            return None, "Rate-limited by Dhan API"
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.Timeout:
        return None, f"Request timed out ({REQUEST_TIMEOUT}s)"
    except requests.exceptions.ConnectionError as exc:
        return None, f"Connection error: {exc}"
    except ValueError as exc:
        return None, f"JSON parse error: {exc}"
    except requests.exceptions.HTTPError as exc:
        return None, f"HTTP error: {exc}"


def fetch_ltp(symbol: str = "NIFTY") -> tuple:
    """Return (ltp_float, error_str)."""
    meta = UNDERLYINGS.get(symbol, UNDERLYINGS["NIFTY"])

    def _call():
        payload = {meta["segment"]: [meta["id"]]}
        data, err = _post(LTP_URL, payload)
        if err:
            raise RuntimeError(err)
        # Navigate response: {segment: {str(id): {lastPrice: ...}}}
        seg_data = data.get(meta["segment"], {})
        rec = seg_data.get(str(meta["id"]), seg_data.get(meta["id"], {}))
        ltp = (
            rec.get("lastPrice")
            or rec.get("ltp")
            or rec.get("last_price")
        )
        if ltp is None:
            raise ValueError(f"LTP key not found in response: {list(rec.keys())}")
        return float(ltp)

    val, err = ttl_cache(f"ltp_{symbol}", _call, ttl=CACHE_TTL)
    return val, err


def fetch_expiry_list(symbol: str = "NIFTY") -> tuple:
    """Return (list_of_expiry_strings, error_str)."""
    meta = UNDERLYINGS.get(symbol, UNDERLYINGS["NIFTY"])

    def _call():
        payload = {"UnderlyingScrip": meta["id"], "UnderlyingSeg": meta["segment"]}
        data, err = _post(EXPIRY_URL, payload)
        if err:
            raise RuntimeError(err)
        expiries = data.get("data", data) if isinstance(data, dict) else data
        if not isinstance(expiries, list) or not expiries:
            raise ValueError("Empty expiry list from API")
        return [str(e) for e in expiries]

    return ttl_cache(f"expiry_{symbol}", _call, ttl=300)


def fetch_option_chain(symbol: str = "NIFTY", expiry: str = None) -> tuple:
    """Return (list_of_strike_rows, error_str)."""
    meta = UNDERLYINGS.get(symbol, UNDERLYINGS["NIFTY"])
    if expiry is None:
        expiries, err = fetch_expiry_list(symbol)
        if err or not expiries:
            return [], err or "No expiry available"
        expiry = expiries[0]

    def _call():
        payload = {
            "UnderlyingScrip": meta["id"],
            "UnderlyingSeg": meta["segment"],
            "Expiry": expiry,
        }
        data, err = _post(OC_URL, payload)
        if err:
            raise RuntimeError(err)
        rows = data.get("data", []) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise ValueError("Unexpected option-chain response format")
        return rows

    return ttl_cache(f"oc_{symbol}_{expiry}", _call, ttl=CACHE_TTL)


# ---------------------------------------------------------------------------
# Technical Signals
# ---------------------------------------------------------------------------
def compute_ema(prices: pd.Series, period: int) -> pd.Series:
    return prices.ewm(span=period, adjust=False).mean()


def compute_vwap(df: pd.DataFrame) -> pd.Series:
    """VWAP = cumsum(price * vol) / cumsum(vol). Requires 'close' and 'volume'.
    NOTE: Returns close price when volume data is unavailable (e.g. synthetic bars).
    """
    if "volume" not in df.columns or df["volume"].sum() == 0:
        return df["close"].copy()
    tp = (df["high"] + df["low"] + df["close"]) / 3
    return (tp * df["volume"]).cumsum() / df["volume"].cumsum()


def compute_momentum(prices: pd.Series, period: int = 10) -> pd.Series:
    return prices.diff(period)


def generate_signals(df: pd.DataFrame) -> dict:
    """Given OHLCV DataFrame return dict of signal values."""
    if df.empty or len(df) < 20:
        return {"ema9": None, "ema21": None, "vwap": None, "momentum": None, "bias": "NEUTRAL"}

    close = df["close"]
    ema9 = compute_ema(close, 9).iloc[-1]
    ema21 = compute_ema(close, 21).iloc[-1]
    vwap = compute_vwap(df).iloc[-1]
    mom = compute_momentum(close, 10).iloc[-1]

    ltp = close.iloc[-1]
    bullish = (ema9 > ema21) and (ltp > vwap) and (mom > 0)
    bearish = (ema9 < ema21) and (ltp < vwap) and (mom < 0)
    bias = "BULLISH" if bullish else ("BEARISH" if bearish else "NEUTRAL")

    return {
        "ema9": round(ema9, 2),
        "ema21": round(ema21, 2),
        "vwap": round(vwap, 2),
        "momentum": round(mom, 2),
        "bias": bias,
    }


# ---------------------------------------------------------------------------
# PCR Calculation
# ---------------------------------------------------------------------------
def compute_pcr(oc_rows: list) -> tuple:
    """Return (pcr_float, total_ce_oi, total_pe_oi)."""
    if not oc_rows:
        return None, 0, 0
    total_ce_oi = sum(
        float(r.get("callOI", r.get("CE_OI", r.get("ce_oi", 0))) or 0) for r in oc_rows
    )
    total_pe_oi = sum(
        float(r.get("putOI", r.get("PE_OI", r.get("pe_oi", 0))) or 0) for r in oc_rows
    )
    pcr = round(total_pe_oi / total_ce_oi, 3) if total_ce_oi else None
    return pcr, int(total_ce_oi), int(total_pe_oi)


# ---------------------------------------------------------------------------
# Smart Strike Selection
# ---------------------------------------------------------------------------
def select_strikes(oc_rows: list, ltp: float, n_otm: int = 3) -> list:
    """Pick ATM + n_otm OTM CE and PE strikes nearest to LTP."""
    if not oc_rows or ltp is None:
        return oc_rows[:10] if oc_rows else []

    def _strike(r):
        return float(r.get("strikePrice", r.get("strike", r.get("Strike", 0))) or 0)

    strikes_sorted = sorted(oc_rows, key=lambda r: abs(_strike(r) - ltp))
    return strikes_sorted[: 1 + n_otm * 2]  # ATM + OTMs on both sides


# ---------------------------------------------------------------------------
# Trade Plan Generator
# ---------------------------------------------------------------------------
def generate_trade_plan(ltp: float, signals: dict, pcr: float) -> str:
    if ltp is None:
        return "⚠️ LTP unavailable – cannot generate trade plan."

    bias = signals.get("bias", "NEUTRAL")
    ema9 = signals.get("ema9")
    vwap = signals.get("vwap")

    lines = [f"📊 Trade Plan  |  LTP: {ltp}  |  Bias: {bias}"]
    lines.append("─" * 55)

    if bias == "BULLISH":
        entry = round(ltp + 5, 2)
        sl = round(vwap * 0.995 if vwap else ltp * 0.995, 2)
        t1 = round(ltp * 1.005, 2)
        t2 = round(ltp * 1.010, 2)
        lines.append(f"Direction : BUY CE")
        lines.append(f"Entry     : >{entry}")
        lines.append(f"Stop-Loss : {sl}  (below VWAP)")
        lines.append(f"Target 1  : {t1}")
        lines.append(f"Target 2  : {t2}")
    elif bias == "BEARISH":
        entry = round(ltp - 5, 2)
        sl = round(vwap * 1.005 if vwap else ltp * 1.005, 2)
        t1 = round(ltp * 0.995, 2)
        t2 = round(ltp * 0.990, 2)
        lines.append(f"Direction : BUY PE")
        lines.append(f"Entry     : <{entry}")
        lines.append(f"Stop-Loss : {sl}  (above VWAP)")
        lines.append(f"Target 1  : {t1}")
        lines.append(f"Target 2  : {t2}")
    else:
        lines.append("Direction : WAIT – no clear trend")
        lines.append("Entry     : –")
        lines.append("Stop-Loss : –")
        lines.append("Target    : –")

    if pcr is not None:
        sentiment = "Bullish" if pcr > 1.2 else ("Bearish" if pcr < 0.8 else "Neutral")
        lines.append(f"PCR       : {pcr}  ({sentiment} sentiment)")

    lines.append(f"Generated : {datetime.now().strftime('%H:%M:%S')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Build candlestick chart from synthetic / in-memory price series
# ---------------------------------------------------------------------------
_price_history: list = []  # rolling list of {"time", "ltp"}


def build_chart(ltp: float, signals: dict) -> go.Figure:
    if ltp is not None:
        _price_history.append({"time": datetime.now(), "ltp": ltp})
        if len(_price_history) > 200:
            _price_history.pop(0)

    fig = go.Figure()
    if len(_price_history) < 2:
        fig.update_layout(
            title="Waiting for data…",
            template="plotly_dark",
            paper_bgcolor="#060606",
            plot_bgcolor="#060606",
        )
        return fig

    df_hist = pd.DataFrame(_price_history)
    # Build synthetic OHLCV by grouping every N ticks
    df_hist["time"] = pd.to_datetime(df_hist["time"])
    df_hist.set_index("time", inplace=True)
    ohlcv = df_hist["ltp"].resample("1min").ohlc()
    ohlcv.columns = ["open", "high", "low", "close"]
    ohlcv["volume"] = 0  # No tick volume from LTP polling; VWAP is close-based
    ohlcv.dropna(inplace=True)

    if not ohlcv.empty:
        fig.add_trace(
            go.Candlestick(
                x=ohlcv.index,
                open=ohlcv["open"],
                high=ohlcv["high"],
                low=ohlcv["low"],
                close=ohlcv["close"],
                name="Price",
                increasing_line_color="#00ff88",
                decreasing_line_color="#ff4466",
            )
        )

        close = ohlcv["close"]
        ema9 = compute_ema(close, 9)
        ema21 = compute_ema(close, 21)
        vwap_vals = compute_vwap(ohlcv)

        fig.add_trace(
            go.Scatter(x=ohlcv.index, y=ema9, mode="lines", name="EMA9",
                       line=dict(color="#ffaa00", width=1.5))
        )
        fig.add_trace(
            go.Scatter(x=ohlcv.index, y=ema21, mode="lines", name="EMA21",
                       line=dict(color="#00aaff", width=1.5))
        )
        fig.add_trace(
            go.Scatter(x=ohlcv.index, y=vwap_vals, mode="lines", name="VWAP",
                       line=dict(color="#ff88ff", width=1.5, dash="dot"))
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#060606",
        plot_bgcolor="#060606",
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


# ---------------------------------------------------------------------------
# Format option-chain rows for DataTable
# ---------------------------------------------------------------------------
def format_oc_table(oc_rows: list, ltp: float = None) -> list:
    table_rows = []
    for r in oc_rows:
        strike = r.get("strikePrice", r.get("strike", r.get("Strike", "–")))
        ce_ltp = (
            r.get("callLTP", r.get("CE_LTP", r.get("ce_ltp", "–")))
        )
        pe_ltp = (
            r.get("putLTP", r.get("PE_LTP", r.get("pe_ltp", "–")))
        )
        ce_oi = (
            r.get("callOI", r.get("CE_OI", r.get("ce_oi", "–")))
        )
        pe_oi = (
            r.get("putOI", r.get("PE_OI", r.get("pe_oi", "–")))
        )
        atm = ""
        if ltp is not None:
            try:
                if abs(float(strike) - ltp) < 50:
                    atm = "◀ ATM"
            except (ValueError, TypeError):
                pass
        table_rows.append({
            "Strike": strike,
            "CE LTP": ce_ltp,
            "CE OI": ce_oi,
            "PE LTP": pe_ltp,
            "PE OI": pe_oi,
            "ATM": atm,
        })
    return table_rows


# ---------------------------------------------------------------------------
# Dash App
# ---------------------------------------------------------------------------
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    title="AI Options Dashboard",
    suppress_callback_exceptions=True,
)
server = app.server  # expose for gunicorn

# ── Layout ──────────────────────────────────────────────────────────────────
SYMBOL_OPTIONS = [{"label": k, "value": k} for k in UNDERLYINGS]

_badge_style = {"fontSize": "0.9rem", "padding": "4px 10px"}

app.layout = dbc.Container(
    fluid=True,
    children=[
        dcc.Interval(id="interval-ltp", interval=2000, n_intervals=0),
        dcc.Interval(id="interval-oc", interval=10000, n_intervals=0),
        dcc.Store(id="store-ltp"),
        dcc.Store(id="store-oc"),
        dcc.Store(id="store-signals"),

        # ── Header ──────────────────────────────────────────────────────────
        dbc.Row(
            dbc.Col(
                html.H2(
                    [
                        html.Span("🚀 ", style={"fontSize": "1.6rem"}),
                        "AI Options Dashboard",
                        dbc.Badge("LIVE", color="success", className="ms-3", style=_badge_style),
                    ],
                    className="my-3 text-center",
                )
            )
        ),

        # ── Controls ────────────────────────────────────────────────────────
        dbc.Row(
            [
                dbc.Col(
                    dbc.Select(
                        id="select-symbol",
                        options=SYMBOL_OPTIONS,
                        value="NIFTY",
                    ),
                    width=2,
                ),
                dbc.Col(
                    dbc.Select(id="select-expiry", options=[], value=None),
                    width=3,
                ),
                dbc.Col(
                    dbc.Button("Refresh", id="btn-refresh", color="primary", size="sm"),
                    width=1,
                ),
                dbc.Col(id="col-ltp", width=6),
            ],
            className="mb-3 align-items-center",
        ),

        # ── Tabs ────────────────────────────────────────────────────────────
        dbc.Tabs(
            [
                dbc.Tab(label="📈 Chart & Signals", tab_id="tab-chart"),
                dbc.Tab(label="⛓ Option Chain", tab_id="tab-oc"),
                dbc.Tab(label="📋 Trade Plan", tab_id="tab-plan"),
            ],
            id="tabs",
            active_tab="tab-chart",
            className="mb-2",
        ),
        html.Div(id="tab-content"),
    ],
)

# ── Tab content ─────────────────────────────────────────────────────────────


def _chart_tab():
    return dbc.Row(
        [
            dbc.Col(
                dcc.Graph(id="graph-candle", style={"height": "450px"}),
                width=9,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        dbc.CardBody(id="card-signals"),
                        className="mb-2",
                    ),
                    dbc.Card(
                        dbc.CardBody(id="card-pcr"),
                    ),
                ],
                width=3,
            ),
        ]
    )


def _oc_tab():
    return dash_table.DataTable(
        id="table-oc",
        columns=[
            {"name": c, "id": c}
            for c in ["Strike", "CE LTP", "CE OI", "PE LTP", "PE OI", "ATM"]
        ],
        data=[],
        style_header={"backgroundColor": "#1a1a2e", "color": "#e0e0e0", "fontWeight": "bold"},
        style_data={"backgroundColor": "#0f0f1f", "color": "#cccccc"},
        style_data_conditional=[
            {
                "if": {"filter_query": '{ATM} contains "ATM"'},
                "backgroundColor": "#1a3a1a",
                "color": "#00ff88",
                "fontWeight": "bold",
            }
        ],
        page_size=20,
        style_table={"overflowX": "auto"},
    )


def _plan_tab():
    return dbc.Card(
        dbc.CardBody(
            html.Pre(id="pre-plan", style={"whiteSpace": "pre-wrap", "color": "#00ff88"})
        )
    )


# ── Callbacks ───────────────────────────────────────────────────────────────


@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab"),
)
def render_tab(active_tab):
    if active_tab == "tab-chart":
        return _chart_tab()
    if active_tab == "tab-oc":
        return _oc_tab()
    return _plan_tab()


@app.callback(
    Output("select-expiry", "options"),
    Output("select-expiry", "value"),
    Input("select-symbol", "value"),
    Input("btn-refresh", "n_clicks"),
)
def update_expiry(symbol, _):
    expiries, err = fetch_expiry_list(symbol or "NIFTY")
    if err or not expiries:
        return [], None
    opts = [{"label": e, "value": e} for e in expiries[:8]]
    return opts, expiries[0]


@app.callback(
    Output("store-ltp", "data"),
    Input("interval-ltp", "n_intervals"),
    State("select-symbol", "value"),
)
def refresh_ltp(_, symbol):
    ltp, err = fetch_ltp(symbol or "NIFTY")
    return {"ltp": ltp, "error": err, "ts": time.time()}


@app.callback(
    Output("store-oc", "data"),
    Input("interval-oc", "n_intervals"),
    Input("btn-refresh", "n_clicks"),
    State("select-symbol", "value"),
    State("select-expiry", "value"),
)
def refresh_oc(_, __, symbol, expiry):
    rows, err = fetch_option_chain(symbol or "NIFTY", expiry)
    return {"rows": rows, "error": err, "ts": time.time()}


@app.callback(
    Output("col-ltp", "children"),
    Input("store-ltp", "data"),
)
def update_ltp_badge(data):
    if not data:
        return dbc.Badge("LTP: –", color="secondary")
    err = data.get("error")
    ltp = data.get("ltp")
    if err:
        return dbc.Badge(f"⚠ {err[:60]}", color="danger")
    return dbc.Badge(
        f"LTP: {ltp:,.2f}" if ltp else "LTP: –",
        color="success",
        style={"fontSize": "1rem"},
    )


@app.callback(
    Output("graph-candle", "figure"),
    Output("card-signals", "children"),
    Output("store-signals", "data"),
    Input("store-ltp", "data"),
    prevent_initial_call=True,
)
def update_chart(ltp_data):
    ltp = ltp_data.get("ltp") if ltp_data else None
    # Build synthetic df from history for signals
    if len(_price_history) >= 2:
        df_h = pd.DataFrame(_price_history)
        df_h["time"] = pd.to_datetime(df_h["time"])
        df_h.set_index("time", inplace=True)
        ohlcv = df_h["ltp"].resample("1min").ohlc()
        ohlcv.columns = ["open", "high", "low", "close"]
        ohlcv["volume"] = 0  # No tick volume from LTP polling; VWAP is close-based
        ohlcv.dropna(inplace=True)
        signals = generate_signals(ohlcv)
    else:
        signals = {"bias": "NEUTRAL", "ema9": None, "ema21": None, "vwap": None, "momentum": None}

    fig = build_chart(ltp, signals)

    bias_color = {"BULLISH": "success", "BEARISH": "danger"}.get(signals["bias"], "secondary")
    sig_children = [
        html.H6("Signals", className="card-title"),
        dbc.Badge(signals["bias"], color=bias_color, className="mb-2 d-block"),
        html.Small(f"EMA9  : {signals['ema9'] or '–'}"),
        html.Br(),
        html.Small(f"EMA21 : {signals['ema21'] or '–'}"),
        html.Br(),
        html.Small(f"VWAP  : {signals['vwap'] or '–'}"),
        html.Br(),
        html.Small(f"Momentum: {signals['momentum'] or '–'}"),
    ]
    return fig, sig_children, signals


@app.callback(
    Output("card-pcr", "children"),
    Output("table-oc", "data"),
    Input("store-oc", "data"),
    State("store-ltp", "data"),
    prevent_initial_call=True,
)
def update_oc(oc_data, ltp_data):
    if not oc_data:
        return [html.Small("PCR: –")], []

    rows = oc_data.get("rows") or []
    err = oc_data.get("error")
    ltp = (ltp_data or {}).get("ltp")

    if err:
        pcr_children = [dbc.Badge(f"⚠ {err[:50]}", color="danger")]
        return pcr_children, []

    pcr, ce_oi, pe_oi = compute_pcr(rows)
    selected = select_strikes(rows, ltp, n_otm=5)
    table_data = format_oc_table(selected, ltp)

    pcr_color = "success" if (pcr or 0) > 1.2 else ("danger" if (pcr or 0) < 0.8 else "warning")
    pcr_children = [
        html.H6("PCR", className="card-title"),
        dbc.Badge(f"{pcr or '–'}", color=pcr_color, className="mb-2"),
        html.Br(),
        html.Small(f"CE OI: {ce_oi:,}"),
        html.Br(),
        html.Small(f"PE OI: {pe_oi:,}"),
    ]
    return pcr_children, table_data


@app.callback(
    Output("pre-plan", "children"),
    Input("store-signals", "data"),
    Input("store-ltp", "data"),
    Input("store-oc", "data"),
    prevent_initial_call=True,
)
def update_plan(signals, ltp_data, oc_data):
    ltp = (ltp_data or {}).get("ltp")
    rows = (oc_data or {}).get("rows") or []
    pcr, _, _ = compute_pcr(rows)
    plan = generate_trade_plan(ltp, signals or {}, pcr)
    return plan


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=PORT)
