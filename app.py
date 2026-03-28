import os
import time
import json
from datetime import datetime, timedelta
from functools import lru_cache
import requests
import pandas as pd
import plotly.graph_objs as go
from dash import Dash, html, dcc, dash_table, Input, Output, State, no_update
import dash_bootstrap_components as dbc

# ─────────────────────────── ENV ───────────────────────────
CLIENT_ID = os.getenv("CLIENT_ID", "")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "")
PORT = int(os.environ.get("PORT", 8050))

# ─────────────────────────── API ───────────────────────────
BASE_URL = "https://api.dhan.co/v2"
LTP_URL = f"{BASE_URL}/marketfeed/ltp"
EXPIRY_URL = f"{BASE_URL}/optionChain/expiryList"
OPTION_CHAIN_URL = f"{BASE_URL}/optionChain"

UNDERLYINGS = {
    "NIFTY": {"id": 13, "segment": "IDX_I", "lot_size": 25, "step": 50},
}

# ─────────────────────────── SESSION ───────────────────────
session = requests.Session()
session.headers.update(
    {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json",
    }
)

# ─────────────────────────── SETTINGS ──────────────────────
LTP_INTERVAL_MS = 1000
OC_INTERVAL_MS = 8000
REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", 5))
MAX_POINTS = 200
OC_CACHE_TTL = 15
EXPIRY_CACHE_TTL = 300
BACKOFF_CAP_MS = 30_000
EMA_SHORT, EMA_MID, EMA_LONG = 9, 21, 50

# ─────────────────────────── CACHE ─────────────────────────
option_cache: dict = {"data": [], "time": 0.0}
expiry_cache: dict = {"code": None, "time": 0.0}
FALLBACK_ROWS = [
    {"Strike": "-", "CE LTP": "-", "PE LTP": "-", "CE OI": "-", "PE OI": "-"}
    for _ in range(10)
]


# ─────────────────────────── HELPERS ───────────────────────
def _api_post(url: str, payload: dict, retries: int = 3) -> requests.Response:
    """POST with exponential backoff and retry."""
    delay = 1.0
    for attempt in range(retries):
        try:
            resp = session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 429:
                time.sleep(delay)
                delay = min(delay * 2, BACKOFF_CAP_MS / 1000)
                continue
            return resp
        except requests.exceptions.RequestException as exc:
            if attempt == retries - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 2, BACKOFF_CAP_MS / 1000)
    raise RuntimeError(f"All {retries} retries failed for {url}")


def fetch_ltp() -> tuple:
    """Return (price: float|None, error: str|None)."""
    try:
        payload = {"NSE_INDEX": [UNDERLYINGS["NIFTY"]["id"]]}
        r = _api_post(LTP_URL, payload)
        r.raise_for_status()
        data = r.json().get("data", {})
        price = None
        if isinstance(data, list) and data:
            price = data[0].get("ltp") or data[0].get("lastPrice")
        elif isinstance(data, dict) and data:
            seg = next(iter(data.values()), {})
            if isinstance(seg, list) and seg:
                price = seg[0].get("ltp") or seg[0].get("lastPrice")
            elif isinstance(seg, dict):
                price = seg.get("ltp") or seg.get("lastPrice")
        if price is None:
            return None, "LTP: empty response"
        return float(price), None
    except Exception as exc:
        return None, f"LTP error: {type(exc).__name__}: {exc}"


def fetch_expiry() -> tuple:
    """Return (expiry_code, error)."""
    now = time.time()
    if expiry_cache["code"] and now - expiry_cache["time"] < EXPIRY_CACHE_TTL:
        return expiry_cache["code"], None
    try:
        payload = {
            "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
            "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
        }
        r = _api_post(EXPIRY_URL, payload)
        r.raise_for_status()
        data = r.json().get("data") or []
        if not data:
            return None, "Expiry: empty data"
        first = data[0]
        code = first.get("expiryCode") if isinstance(first, dict) else first
        expiry_cache["code"] = code
        expiry_cache["time"] = now
        return code, None
    except Exception as exc:
        return None, f"Expiry error: {type(exc).__name__}: {exc}"


def _safe_float(val):
    try:
        return float(val) if val not in (None, "", "-") else None
    except (ValueError, TypeError):
        return None


def fetch_option_chain() -> tuple:
    """Return (rows: list[dict], error: str|None)."""
    now = time.time()
    if option_cache["data"] and now - option_cache["time"] < OC_CACHE_TTL:
        return option_cache["data"], None

    expiry_code, err = fetch_expiry()
    if err:
        return FALLBACK_ROWS, err

    try:
        payload = {
            "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
            "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
            "ExpiryCode": expiry_code,
        }
        r = _api_post(OPTION_CHAIN_URL, payload)
        r.raise_for_status()
        data = r.json().get("data") or []
        if not data:
            return FALLBACK_ROWS, "Option chain: empty data"

        rows = []
        for item in data:
            ce = item.get("CE") or {}
            pe = item.get("PE") or {}
            rows.append(
                {
                    "Strike": item.get("strikePrice"),
                    "CE LTP": _safe_float(ce.get("ltp") or ce.get("lastPrice")),
                    "CE OI": _safe_float(ce.get("openInterest") or ce.get("oi")),
                    "CE IV": _safe_float(ce.get("impliedVolatility") or ce.get("iv")),
                    "PE LTP": _safe_float(pe.get("ltp") or pe.get("lastPrice")),
                    "PE OI": _safe_float(pe.get("openInterest") or pe.get("oi")),
                    "PE IV": _safe_float(pe.get("impliedVolatility") or pe.get("iv")),
                }
            )
        option_cache["data"] = rows
        option_cache["time"] = now
        return rows, None
    except Exception as exc:
        return FALLBACK_ROWS, f"OC error: {type(exc).__name__}: {exc}"


# ─────────────────────────── TECHNICAL INDICATORS ──────────────────────────
def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df["high"] + df["low"] + df["price"]) / 3
    cumvol = df["volume"].cumsum().replace(0, float("nan"))
    return (tp * df["volume"]).cumsum() / cumvol


def compute_indicators(history: list) -> pd.DataFrame:
    df = pd.DataFrame(history)
    if df.empty or "price" not in df.columns:
        return df
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    if "high" not in df.columns:
        df["high"] = df["price"]
    if "low" not in df.columns:
        df["low"] = df["price"]
    if "volume" not in df.columns:
        df["volume"] = 0.0
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
    df["ema9"] = _ema(df["price"], EMA_SHORT)
    df["ema21"] = _ema(df["price"], EMA_MID)
    df["ema50"] = _ema(df["price"], EMA_LONG)
    df["vwap"] = _vwap(df)
    return df


def compute_signal(df: pd.DataFrame) -> dict:
    """Return scoring signal dict from EMA + VWAP + momentum."""
    if df.empty or len(df) < EMA_LONG:
        return {"signal": "NEUTRAL", "score": 0, "reason": "Insufficient data"}

    row = df.iloc[-1]
    price = row["price"]
    score = 0
    reasons = []

    # EMA stacking
    if row["ema9"] > row["ema21"] > row["ema50"]:
        score += 2
        reasons.append("EMA bullish stack")
    elif row["ema9"] < row["ema21"] < row["ema50"]:
        score -= 2
        reasons.append("EMA bearish stack")

    # Price vs VWAP
    if pd.notna(row.get("vwap")) and row["vwap"] > 0:
        if price > row["vwap"]:
            score += 1
            reasons.append("Above VWAP")
        else:
            score -= 1
            reasons.append("Below VWAP")

    # Price vs EMA9
    if price > row["ema9"]:
        score += 1
        reasons.append("Price > EMA9")
    else:
        score -= 1
        reasons.append("Price < EMA9")

    # Momentum (last 5 candles)
    if len(df) >= 5:
        momentum = df["price"].iloc[-1] - df["price"].iloc[-5]
        if momentum > 0:
            score += 1
            reasons.append(f"Momentum +{momentum:.1f}")
        else:
            score -= 1
            reasons.append(f"Momentum {momentum:.1f}")

    if score >= 3:
        signal = "STRONG BUY"
    elif score >= 1:
        signal = "BUY"
    elif score <= -3:
        signal = "STRONG SELL"
    elif score <= -1:
        signal = "SELL"
    else:
        signal = "NEUTRAL"

    return {"signal": signal, "score": score, "reason": " | ".join(reasons)}


# ─────────────────────────── PCR ───────────────────────────
def compute_pcr(oc_rows: list) -> float | None:
    total_ce_oi = sum(
        r["CE OI"] for r in oc_rows if isinstance(r.get("CE OI"), (int, float))
    )
    total_pe_oi = sum(
        r["PE OI"] for r in oc_rows if isinstance(r.get("PE OI"), (int, float))
    )
    if total_ce_oi and total_ce_oi > 0:
        return round(total_pe_oi / total_ce_oi, 3)
    return None


# ─────────────────────────── SMART STRIKE SELECTION ────────────────────────
def smart_strikes(oc_rows: list, spot: float | None, top_n: int = 5) -> list:
    """Select top-N strikes by OI + proximity to spot."""
    if not oc_rows or spot is None:
        return oc_rows[:top_n] if oc_rows else []
    step = UNDERLYINGS["NIFTY"]["step"]
    scored = []
    for r in oc_rows:
        strike = _safe_float(r.get("Strike"))
        if strike is None:
            continue
        proximity_score = 1 / (1 + abs(strike - spot) / step)
        ce_oi = r.get("CE OI") or 0
        pe_oi = r.get("PE OI") or 0
        oi_score = (ce_oi + pe_oi) / 1e6 if isinstance(ce_oi, float) else 0
        total = proximity_score * 0.6 + oi_score * 0.4
        scored.append((total, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:top_n]]


# ─────────────────────────── TRADE PLAN ────────────────────
def generate_trade_plan(signal: dict, spot: float | None, oc_rows: list) -> str:
    if spot is None:
        return "⚠️ No LTP data available for trade plan."
    sig = signal.get("signal", "NEUTRAL")
    step = UNDERLYINGS["NIFTY"]["step"]
    atm = round(spot / step) * step
    sl_pct = 0.005
    tgt_pct = 0.01
    lot = UNDERLYINGS["NIFTY"]["lot_size"]

    if "BUY" in sig:
        direction = "CE (Call)"
        strike = atm
        sl = round(spot * (1 - sl_pct), 1)
        tgt = round(spot * (1 + tgt_pct), 1)
    elif "SELL" in sig:
        direction = "PE (Put)"
        strike = atm
        sl = round(spot * (1 + sl_pct), 1)
        tgt = round(spot * (1 - tgt_pct), 1)
    else:
        return "📊 Signal: NEUTRAL — No trade recommended at this time."

    lines = [
        f"📌 **Trade Plan — {sig}**",
        f"  Instrument: NIFTY {strike} {direction}",
        f"  Spot: {spot:.2f}  |  ATM Strike: {strike}",
        f"  Entry: ~market  |  SL: {sl}  |  Target: {tgt}",
        f"  Lot Size: {lot}  |  Risk/Reward: ~1:2",
        f"  Reason: {signal.get('reason', '-')}",
    ]
    return "\n".join(lines)


# ─────────────────────────── CHART BUILDERS ────────────────
def _empty_figure(title: str = "") -> go.Figure:
    return go.Figure(
        layout=go.Layout(
            template="plotly_dark",
            title=title,
            paper_bgcolor="#1a1a2e",
            plot_bgcolor="#16213e",
            margin={"l": 50, "r": 20, "t": 40, "b": 40},
        )
    )


def build_price_chart(history: list) -> go.Figure:
    if not history:
        return _empty_figure("📈 Live NIFTY Chart")

    df = compute_indicators(history)
    if df.empty:
        return _empty_figure("📈 Live NIFTY Chart")

    fig = go.Figure()

    # OHLC simulation: use price as close; derive open/high/low from rolling window
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["price"],
            mode="lines",
            name="Price",
            line={"color": "#00d4ff", "width": 2},
        )
    )

    # EMA traces
    for span, col, color in [
        (EMA_SHORT, "ema9", "#ffd700"),
        (EMA_MID, "ema21", "#ff6b35"),
        (EMA_LONG, "ema50", "#a855f7"),
    ]:
        if col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df[col],
                    mode="lines",
                    name=f"EMA{span}",
                    line={"color": color, "width": 1, "dash": "dot"},
                )
            )

    # VWAP
    if "vwap" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["time"],
                y=df["vwap"],
                mode="lines",
                name="VWAP",
                line={"color": "#00ff88", "width": 1.5, "dash": "dash"},
            )
        )

    # Prev high / low bands
    if len(df) >= 2:
        prev_high = df["high"].max()
        prev_low = df["low"].min()
        fig.add_hline(
            y=prev_high,
            line_dash="dot",
            line_color="#ff4444",
            annotation_text="High",
            annotation_position="right",
        )
        fig.add_hline(
            y=prev_low,
            line_dash="dot",
            line_color="#44ff44",
            annotation_text="Low",
            annotation_position="right",
        )

    fig.update_layout(
        template="plotly_dark",
        title="📈 Live NIFTY Chart",
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#16213e",
        xaxis_title="Time",
        yaxis_title="Price",
        legend={"orientation": "h", "y": -0.15},
        margin={"l": 60, "r": 20, "t": 50, "b": 60},
        hovermode="x unified",
    )
    return fig


def build_volume_chart(history: list) -> go.Figure:
    if not history:
        return _empty_figure("🔊 Tick Volume")
    df = pd.DataFrame(history)
    if "volume" not in df.columns or df["volume"].sum() == 0:
        return _empty_figure("🔊 Tick Volume (no data)")
    fig = go.Figure(
        data=[
            go.Bar(
                x=df["time"],
                y=df["volume"],
                name="Volume",
                marker_color="#5bc0de",
            )
        ]
    )
    fig.update_layout(
        template="plotly_dark",
        title="🔊 Tick Volume",
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#16213e",
        margin={"l": 50, "r": 20, "t": 40, "b": 40},
    )
    return fig


def build_oc_chart(oc_rows: list, spot: float | None) -> go.Figure:
    if not oc_rows or oc_rows == FALLBACK_ROWS:
        return _empty_figure("📊 OI Distribution")
    strikes, ce_oi, pe_oi = [], [], []
    for r in oc_rows:
        s = _safe_float(r.get("Strike"))
        if s is None:
            continue
        strikes.append(s)
        ce_oi.append(r.get("CE OI") or 0)
        pe_oi.append(r.get("PE OI") or 0)

    if not strikes:
        return _empty_figure("📊 OI Distribution")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=strikes, y=ce_oi, name="CE OI", marker_color="#ff6b35", opacity=0.75)
    )
    fig.add_trace(
        go.Bar(x=strikes, y=pe_oi, name="PE OI", marker_color="#5bc0de", opacity=0.75)
    )
    if spot is not None:
        fig.add_vline(
            x=spot,
            line_dash="dash",
            line_color="white",
            annotation_text="Spot",
        )
    fig.update_layout(
        template="plotly_dark",
        title="📊 OI Distribution",
        barmode="group",
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#16213e",
        xaxis_title="Strike",
        yaxis_title="Open Interest",
        margin={"l": 60, "r": 20, "t": 50, "b": 50},
    )
    return fig


# ─────────────────────────── BACKOFF HELPER ────────────────
def next_interval(prev_ms: int, failed: bool) -> int:
    if not failed:
        return LTP_INTERVAL_MS
    return int(min(prev_ms * 2, BACKOFF_CAP_MS))


# ─────────────────────────── APP LAYOUT ────────────────────
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True,
)
server = app.server  # required for gunicorn

_badge_style = {
    "fontSize": "1.1rem",
    "padding": "6px 14px",
    "borderRadius": "8px",
}

app.layout = dbc.Container(
    fluid=True,
    style={"backgroundColor": "#0d0d1a", "minHeight": "100vh", "paddingBottom": "2rem"},
    children=[
        # ── Header ────────────────────────────────────────────
        dbc.Row(
            dbc.Col(
                html.H2(
                    "🚀 AI Trading Dashboard — NIFTY",
                    className="text-center text-info my-3",
                )
            )
        ),
        # ── Metric Cards ──────────────────────────────────────
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.P("LTP", className="card-title text-muted mb-1"),
                                html.H4(id="ltp-display", children="—", className="text-info"),
                            ]
                        ),
                        color="dark",
                        outline=True,
                    ),
                    width=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.P("Signal", className="card-title text-muted mb-1"),
                                html.H4(id="signal-display", children="—", className="text-warning"),
                            ]
                        ),
                        color="dark",
                        outline=True,
                    ),
                    width=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.P("PCR", className="card-title text-muted mb-1"),
                                html.H4(id="pcr-display", children="—", className="text-success"),
                            ]
                        ),
                        color="dark",
                        outline=True,
                    ),
                    width=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.P("Status", className="card-title text-muted mb-1"),
                                dbc.Badge(id="status-badge", children="…", color="secondary", style=_badge_style),
                            ]
                        ),
                        color="dark",
                        outline=True,
                    ),
                    width=3,
                ),
            ],
            className="mb-3 g-2",
        ),
        # ── Price Chart ───────────────────────────────────────
        dbc.Row(
            dbc.Col(
                dcc.Graph(id="price-chart", figure=_empty_figure("📈 Live NIFTY Chart"), config={"displayModeBar": True}),
            )
        ),
        # ── Volume + OI Charts ────────────────────────────────
        dbc.Row(
            [
                dbc.Col(
                    dcc.Graph(id="volume-chart", figure=_empty_figure("🔊 Tick Volume"), config={"displayModeBar": False}),
                    md=5,
                ),
                dbc.Col(
                    dcc.Graph(id="oi-chart", figure=_empty_figure("📊 OI Distribution"), config={"displayModeBar": False}),
                    md=7,
                ),
            ],
            className="mt-2",
        ),
        # ── Trade Plan ────────────────────────────────────────
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H6("🗂️ Trade Plan", className="text-warning"),
                            html.Pre(
                                id="trade-plan",
                                style={
                                    "color": "#ccc",
                                    "whiteSpace": "pre-wrap",
                                    "fontSize": "0.85rem",
                                    "margin": 0,
                                },
                            ),
                        ]
                    ),
                    color="dark",
                    outline=True,
                ),
                className="mt-2",
            )
        ),
        # ── Option Chain Table ────────────────────────────────
        dbc.Row(
            dbc.Col(
                [
                    html.H6("📋 Option Chain", className="text-info mt-3"),
                    dash_table.DataTable(
                        id="oc-table",
                        columns=[
                            {"name": c, "id": c}
                            for c in ["Strike", "CE LTP", "CE OI", "CE IV", "PE LTP", "PE OI", "PE IV"]
                        ],
                        page_size=20,
                        style_table={"overflowX": "auto"},
                        style_cell={
                            "backgroundColor": "#111",
                            "color": "#eee",
                            "textAlign": "center",
                            "border": "1px solid #333",
                            "fontSize": "0.8rem",
                        },
                        style_header={
                            "backgroundColor": "#1a1a2e",
                            "color": "#00d4ff",
                            "fontWeight": "bold",
                        },
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": "#161625",
                            }
                        ],
                    ),
                ]
            )
        ),
        # ── Hidden stores & intervals ─────────────────────────
        dcc.Store(id="history-store", data=[]),
        dcc.Store(id="oc-store", data=[]),
        dcc.Store(id="spot-store", data=None),
        dcc.Interval(id="ltp-interval", interval=LTP_INTERVAL_MS, n_intervals=0),
        dcc.Interval(id="oc-interval", interval=OC_INTERVAL_MS, n_intervals=0),
    ],
)


# ─────────────────────────── CALLBACKS ─────────────────────
@app.callback(
    Output("ltp-display", "children"),
    Output("status-badge", "children"),
    Output("status-badge", "color"),
    Output("price-chart", "figure"),
    Output("volume-chart", "figure"),
    Output("signal-display", "children"),
    Output("trade-plan", "children"),
    Output("history-store", "data"),
    Output("spot-store", "data"),
    Output("ltp-interval", "interval"),
    Input("ltp-interval", "n_intervals"),
    State("history-store", "data"),
    State("ltp-interval", "interval"),
    State("oc-store", "data"),
    prevent_initial_call=False,
)
def update_ltp(_n, history, current_interval, oc_rows):
    history = history or []
    oc_rows = oc_rows or []

    ltp, err = fetch_ltp()

    if err or ltp is None:
        new_interval = next_interval(current_interval, failed=True)
        fig_price = build_price_chart(history)
        fig_vol = build_volume_chart(history)
        sig_info = compute_signal(compute_indicators(history))
        plan = generate_trade_plan(sig_info, None, oc_rows)
        return (
            "ERROR",
            err or "LTP failed",
            "danger",
            fig_price,
            fig_vol,
            sig_info.get("signal", "—"),
            plan,
            history,
            None,
            new_interval,
        )

    timestamp = datetime.now().strftime("%H:%M:%S")
    history.append({"time": timestamp, "price": ltp, "high": ltp, "low": ltp, "volume": 0})
    history = history[-MAX_POINTS:]

    df = compute_indicators(history)
    sig_info = compute_signal(df)
    plan = generate_trade_plan(sig_info, ltp, oc_rows)

    return (
        f"{ltp:,.2f}",
        "LIVE",
        "success",
        build_price_chart(history),
        build_volume_chart(history),
        sig_info.get("signal", "NEUTRAL"),
        plan,
        history,
        ltp,
        LTP_INTERVAL_MS,
    )


@app.callback(
    Output("oc-table", "data"),
    Output("oi-chart", "figure"),
    Output("pcr-display", "children"),
    Output("oc-store", "data"),
    Output("oc-interval", "interval"),
    Input("oc-interval", "n_intervals"),
    State("oc-interval", "interval"),
    State("spot-store", "data"),
    prevent_initial_call=False,
)
def update_option_chain(_n, current_interval, spot):
    rows, err = fetch_option_chain()
    pcr = compute_pcr(rows)
    pcr_text = f"{pcr:.3f}" if pcr is not None else "—"

    selected = smart_strikes(rows, spot, top_n=20)
    oi_fig = build_oc_chart(selected, spot)

    # Format rows for table display
    display_rows = []
    for r in selected:
        display_rows.append(
            {
                "Strike": r.get("Strike", "-"),
                "CE LTP": r.get("CE LTP") or "-",
                "CE OI": r.get("CE OI") or "-",
                "CE IV": r.get("CE IV") or "-",
                "PE LTP": r.get("PE LTP") or "-",
                "PE OI": r.get("PE OI") or "-",
                "PE IV": r.get("PE IV") or "-",
            }
        )

    if err:
        new_int = next_interval(current_interval, failed=True)
        return display_rows, oi_fig, pcr_text, rows, new_int

    return display_rows, oi_fig, pcr_text, rows, OC_INTERVAL_MS


# ─────────────────────────── ENTRY POINT ───────────────────
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
    )
