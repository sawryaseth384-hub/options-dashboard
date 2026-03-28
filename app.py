"""
Production-ready Dash AI Trading Dashboard
Dhan API — NIFTY LTP + Option Chain + EMA/VWAP/Momentum Signals
Deploy: gunicorn app:server --bind 0.0.0.0:$PORT
Env vars: CLIENT_ID, DHAN_ACCESS_TOKEN, PORT
"""
import os
import time
import logging
from datetime import datetime, date

import pandas as pd
import requests
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from dash import Dash, html, dcc, dash_table, Input, Output, State, ctx, no_update
import dash_bootstrap_components as dbc

# ─────────────────────────── LOGGING ────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")

# ─────────────────────────── ENV ────────────────────────────
CLIENT_ID = os.getenv("CLIENT_ID", "")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "")
PORT = int(os.getenv("PORT", 8050))

HEADERS = {
    "access-token": DHAN_ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
}

# ─────────────────────────── API ENDPOINTS ──────────────────
LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
EXPIRY_URL = "https://api.dhan.co/v2/optionChain/expiryList"
OC_URL = "https://api.dhan.co/v2/optionChain"
INTRADAY_URL = "https://api.dhan.co/v2/charts/intraday"

NIFTY_ID = 13
NIFTY_OC_SEG = "IDX_I"       # segment key for option chain API
NIFTY_FEED_SEG = "NSE_INDEX"  # segment key for marketfeed/LTP

# ─────────────────────────── SETTINGS ───────────────────────
LTP_INTERVAL_MS = 2000
OC_INTERVAL_MS = 10000
CHART_INTERVAL_MS = 60000
REQUEST_TIMEOUT = 5
MAX_HISTORY = 300
OC_CACHE_TTL = 15
EXPIRY_CACHE_TTL = 300
HIST_CACHE_TTL = 60
BACKOFF_CAP_MS = 60000
STRIKE_RANGE_THRESHOLD = 500  # max points from ATM for smart strike selection

# ─────────────────────────── IN-MEMORY CACHE ────────────────
_expiry_cache: dict = {"code": None, "ts": 0.0}
_oc_cache: dict = {"rows": [], "ts": 0.0}
_hist_cache: dict = {"df": None, "ts": 0.0}

# ─────────────────────────── UTILITIES ──────────────────────
def _safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _backoff(prev_ms: int, failed: bool, default_ms: int) -> int:
    if not failed:
        return default_ms
    return min(prev_ms * 2, BACKOFF_CAP_MS)


def _empty_figure(title: str = "Chart") -> go.Figure:
    """Return a dark empty figure so the UI never breaks."""
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#16213e",
        title=title,
        margin=dict(l=40, r=40, t=50, b=30),
    )
    return fig


# ─────────────────────────── API CALLS ──────────────────────
def fetch_ltp():
    """Fetch NIFTY LTP. Returns (price: float | None, error: str | None)."""
    try:
        r = requests.post(
            LTP_URL,
            headers=HEADERS,
            json={"NSE_INDEX": [NIFTY_ID]},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json().get("data", {})
        price = None
        if isinstance(data, list) and data:
            price = data[0].get("ltp") or data[0].get("lastPrice")
        elif isinstance(data, dict):
            seg = data.get("NSE_INDEX") or next(iter(data.values()), {})
            if isinstance(seg, list) and seg:
                price = seg[0].get("ltp") or seg[0].get("lastPrice")
            elif isinstance(seg, dict):
                price = seg.get("ltp") or seg.get("lastPrice")
        if price is None:
            return None, "LTP not found in response"
        return float(price), None
    except Exception as exc:
        return None, f"LTP error: {exc}"


def fetch_expiry():
    """Fetch nearest expiry code with in-memory caching."""
    now = time.time()
    if _expiry_cache["code"] and now - _expiry_cache["ts"] < EXPIRY_CACHE_TTL:
        return _expiry_cache["code"], None
    try:
        r = requests.post(
            EXPIRY_URL,
            headers=HEADERS,
            json={"UnderlyingScrip": NIFTY_ID, "UnderlyingSeg": NIFTY_OC_SEG},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            return None, "No expiry data returned"
        first = data[0]
        code = first.get("expiryCode") if isinstance(first, dict) else first
        _expiry_cache["code"] = code
        _expiry_cache["ts"] = now
        return code, None
    except Exception as exc:
        return None, f"Expiry error: {exc}"


def fetch_option_chain():
    """Fetch full option chain with in-memory caching. Returns (rows, error)."""
    now = time.time()
    if _oc_cache["rows"] and now - _oc_cache["ts"] < OC_CACHE_TTL:
        return _oc_cache["rows"], None

    expiry, err = fetch_expiry()
    if err:
        return [], err

    try:
        r = requests.post(
            OC_URL,
            headers=HEADERS,
            json={
                "UnderlyingScrip": NIFTY_ID,
                "UnderlyingSeg": NIFTY_OC_SEG,
                "ExpiryCode": expiry,
            },
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            return [], "Option chain returned empty data"

        rows = []
        for item in data:
            strike = _safe_float(item.get("strikePrice"))
            ce = item.get("CE") or item.get("callOption") or {}
            pe = item.get("PE") or item.get("putOption") or {}
            rows.append({
                "strike": strike,
                "ce_ltp": _safe_float(
                    ce.get("ltp") or ce.get("lastPrice") or ce.get("price")
                ),
                "pe_ltp": _safe_float(
                    pe.get("ltp") or pe.get("lastPrice") or pe.get("price")
                ),
                "ce_oi": _safe_float(ce.get("openInterest") or ce.get("oi")) or 0.0,
                "pe_oi": _safe_float(pe.get("openInterest") or pe.get("oi")) or 0.0,
            })

        _oc_cache["rows"] = rows
        _oc_cache["ts"] = now
        log.info("Option chain fetched: %d strikes", len(rows))
        return rows, None
    except Exception as exc:
        return [], f"OC error: {exc}"


def fetch_intraday_chart():
    """Fetch 1-min OHLCV intraday data. Returns DataFrame (may be empty)."""
    now = time.time()
    if _hist_cache["df"] is not None and now - _hist_cache["ts"] < HIST_CACHE_TTL:
        return _hist_cache["df"]

    today = date.today().strftime("%Y-%m-%d")
    try:
        r = requests.post(
            INTRADAY_URL,
            headers=HEADERS,
            json={
                "securityId": str(NIFTY_ID),
                "exchangeSegment": NIFTY_FEED_SEG,
                "instrument": "INDEX",
                "interval": "1",
                "fromDate": today,
                "toDate": today,
            },
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        body = r.json()
        data = body.get("data") if "data" in body else body

        opens = data.get("open") or data.get("o") or []
        highs = data.get("high") or data.get("h") or []
        lows = data.get("low") or data.get("l") or []
        closes = data.get("close") or data.get("c") or []
        volumes = data.get("volume") or data.get("v") or []
        timestamps = data.get("timestamp") or data.get("t") or []

        if not closes:
            return pd.DataFrame()

        df = pd.DataFrame({
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes if volumes else [0] * len(closes),
            "ts": pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("Asia/Kolkata"),
        }).dropna(subset=["close"]).reset_index(drop=True)

        _hist_cache["df"] = df
        _hist_cache["ts"] = now
        return df
    except Exception as exc:
        log.warning("Intraday chart error: %s", exc)
        return pd.DataFrame()


# ─────────────────────────── INDICATORS ─────────────────────
def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _vwap(df: pd.DataFrame) -> pd.Series:
    """Cumulative VWAP from session start."""
    if df.empty or "volume" not in df.columns:
        return pd.Series(dtype=float)
    typical = (df["high"] + df["low"] + df["close"]) / 3
    cum_vol = df["volume"].cumsum().replace(0, float("nan"))
    return (typical * df["volume"]).cumsum() / cum_vol


# ─────────────────────────── AI SIGNAL ──────────────────────
def calc_signal(history: list, pcr: float) -> dict:
    """
    Compute AI signal from LTP history + PCR.
    Uses: EMA-21, VWAP approx, Momentum, EMA cross, PCR sentiment.
    """
    default = {"signal": "NEUTRAL", "entry": "NEUTRAL", "score": 0, "confidence": 0, "trend": "Sideways"}
    if len(history) < 22:
        return default

    prices = pd.Series([h["price"] for h in history])
    last = float(prices.iloc[-1])
    ema21 = float(_ema(prices, 21).iloc[-1])
    ema9 = float(_ema(prices, 9).iloc[-1])
    # Mean price used as VWAP proxy (no tick volume available from LTP history)
    price_avg = float(prices.mean())
    momentum = float(prices.iloc[-1] - prices.iloc[-6]) if len(prices) >= 6 else 0.0

    score = 0
    score += 1 if last > ema21 else -1           # Price vs EMA-21
    score += 1 if last > price_avg else -1        # Price vs mean-price VWAP proxy
    score += 1 if momentum > 0 else (-1 if momentum < 0 else 0)  # Momentum
    score += 1 if ema9 > ema21 else -1            # EMA cross
    if pcr > 1.2:
        score += 1     # heavy put OI → floor support → bullish
    elif pcr < 0.8:
        score -= 1     # heavy call OI → ceiling resistance → bearish

    if score >= 3:
        sig, entry, trend = "STRONG BUY", "CALL BUY", "Bullish"
    elif score >= 1:
        sig, entry, trend = "WEAK BUY", "CALL BUY", "Slightly Bullish"
    elif score == 0:
        sig, entry, trend = "NEUTRAL", "NEUTRAL", "Sideways"
    elif score >= -2:
        sig, entry, trend = "WEAK SELL", "PUT BUY", "Slightly Bearish"
    else:
        sig, entry, trend = "STRONG SELL", "PUT BUY", "Bearish"

    return {
        "signal": sig,
        "entry": entry,
        "score": score,
        "confidence": min(100, abs(score) * 20),
        "trend": trend,
    }


# ─────────────────────────── PCR ────────────────────────────
def calc_pcr(rows: list) -> float:
    if not rows:
        return 1.0
    total_ce = sum(r.get("ce_oi") or 0 for r in rows)
    total_pe = sum(r.get("pe_oi") or 0 for r in rows)
    return round(total_pe / total_ce, 2) if total_ce > 0 else 1.0


# ─────────────────────────── DELTA & STRIKE SELECT ──────────
def estimate_delta(strike: float, spot: float, is_call: bool) -> float:
    """Simple linear delta approximation around ATM."""
    if not spot:
        return 0.5 if is_call else -0.5
    diff = (strike - spot) / max(spot * 0.01, 1)
    raw = max(0.05, min(0.95, 0.5 - diff * 0.1))
    return round(raw if is_call else raw - 1.0, 2)


def select_smart_strike(rows: list, spot: float, side: str):
    """Select best CALL (CE) or PUT (PE) strike by combined score."""
    if not rows or not spot:
        return None

    atm = round(spot / 50) * 50
    candidates = [r for r in rows if r.get("strike") and abs(r["strike"] - atm) <= STRIKE_RANGE_THRESHOLD]
    if not candidates:
        candidates = rows

    max_oi = max(
        (r.get("ce_oi" if side == "CE" else "pe_oi") or 0 for r in candidates),
        default=1,
    ) or 1

    scored = []
    for r in candidates:
        strike = r["strike"]
        if not strike:
            continue
        ltp = r.get("ce_ltp") if side == "CE" else r.get("pe_ltp")
        if not ltp:
            continue

        delta = estimate_delta(strike, spot, side == "CE")
        oi = r.get("ce_oi" if side == "CE" else "pe_oi") or 0
        target_delta = 0.4 if side == "CE" else -0.4

        delta_score = 1.0 - abs(delta - target_delta) * 2
        prox_score = 1.0 - abs(strike - atm) / max(STRIKE_RANGE_THRESHOLD, abs(strike - atm) + 1)
        oi_score = oi / max_oi

        total = delta_score * 0.4 + prox_score * 0.3 + oi_score * 0.3
        scored.append((total, {"strike": strike, "ltp": ltp, "delta": delta, "oi": oi}))

    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


# ─────────────────────────── TRADE PLAN ─────────────────────
def build_trade_plan(strike_info, side: str) -> dict:
    """Generate entry / SL / Target-1 / Target-2."""
    empty = {"strike": "-", "entry": "-", "sl": "-", "t1": "-", "t2": "-", "delta": "-", "oi": 0}
    if not strike_info:
        return empty
    entry = strike_info.get("ltp") or 0
    if not entry:
        return {**empty, "strike": strike_info.get("strike", "-")}
    return {
        "strike": strike_info.get("strike"),
        "entry": round(entry, 2),
        "sl": round(entry * 0.70, 2),
        "t1": round(entry * 1.50, 2),
        "t2": round(entry * 2.00, 2),
        "delta": strike_info.get("delta", "-"),
        "oi": int(strike_info.get("oi", 0) or 0),
    }


# ─────────────────────────── CHARTS ─────────────────────────
def build_price_chart(history: list, chart_type: str) -> go.Figure:
    """Build price chart; never raises — always returns a valid Figure."""
    try:
        if chart_type == "candlestick":
            df = fetch_intraday_chart()
            if not df.empty:
                return _candlestick_figure(df)
        if history:
            return _line_figure(history)
    except Exception as exc:
        log.error("Chart build error: %s", exc)
    return _empty_figure("NIFTY Price")


def _candlestick_figure(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.04,
        subplot_titles=["NIFTY 1-Min Candles", "Volume"],
    )

    fig.add_trace(
        go.Candlestick(
            x=df["ts"],
            open=df["open"], high=df["high"], low=df["low"], close=df["close"],
            name="NIFTY",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
            increasing_fillcolor="#26a69a",
            decreasing_fillcolor="#ef5350",
        ),
        row=1, col=1,
    )

    closes = df["close"]
    for period, color in [(9, "#f7b500"), (21, "#e040fb"), (50, "#00e5ff")]:
        fig.add_trace(
            go.Scatter(
                x=df["ts"], y=_ema(closes, period),
                name=f"EMA{period}",
                line=dict(color=color, width=1.2),
            ),
            row=1, col=1,
        )

    vwap_series = _vwap(df)
    if not vwap_series.empty:
        fig.add_trace(
            go.Scatter(
                x=df["ts"], y=vwap_series,
                name="VWAP",
                line=dict(color="#ff6b35", width=1.5, dash="dot"),
            ),
            row=1, col=1,
        )

    # Day high / low reference lines
    fig.add_hline(
        y=float(df["high"].max()), line_dash="dash", line_color="#888",
        annotation_text="Day High", row=1, col=1,
    )
    fig.add_hline(
        y=float(df["low"].min()), line_dash="dash", line_color="#888",
        annotation_text="Day Low", row=1, col=1,
    )

    bar_colors = [
        "#26a69a" if c >= o else "#ef5350"
        for c, o in zip(df["close"], df["open"])
    ]
    fig.add_trace(
        go.Bar(x=df["ts"], y=df["volume"], name="Volume", marker_color=bar_colors, opacity=0.7),
        row=2, col=1,
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#16213e",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=40, r=40, t=60, b=30),
        height=500,
    )
    return fig


def _line_figure(history: list) -> go.Figure:
    df = pd.DataFrame(history)
    prices = df["price"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["time"], y=prices,
        name="LTP",
        line=dict(color="#00e5ff", width=2),
        fill="tozeroy",
        fillcolor="rgba(0,229,255,0.04)",
    ))

    for period, color in [(9, "#f7b500"), (21, "#e040fb"), (50, "#00e5ff")]:
        if len(prices) >= period:
            fig.add_trace(go.Scatter(
                x=df["time"], y=_ema(prices, period),
                name=f"EMA{period}",
                line=dict(color=color, width=1.2, dash="dot"),
            ))

    if len(prices) > 1:
        # Mean price used as VWAP proxy (no tick volume available from LTP history)
        price_avg = float(prices.mean())
        fig.add_hline(
            y=price_avg,
            line_dash="dash",
            line_color="#ff6b35",
            annotation_text=f"VWAP≈{price_avg:.0f}",
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#16213e",
        title="NIFTY Live Price",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=40, r=40, t=60, b=30),
        height=380,
    )
    return fig


# ─────────────────────────── OC TABLE DATA ──────────────────
def build_oc_table_data(rows: list, spot: float):
    """Return (table_rows, style_data_conditional) for DataTable."""
    if not rows or not spot:
        return [], []

    atm = round(spot / 50) * 50
    max_ce_oi = max((r.get("ce_oi") or 0 for r in rows), default=0)
    max_pe_oi = max((r.get("pe_oi") or 0 for r in rows), default=0)

    table_rows, styles = [], []
    for idx, r in enumerate(rows):
        strike = r.get("strike")
        if not strike:
            continue

        table_rows.append({
            "Strike": int(strike),
            "CE LTP": round(r.get("ce_ltp") or 0, 2) or "-",
            "PE LTP": round(r.get("pe_ltp") or 0, 2) or "-",
            "CE OI": f"{int(r.get('ce_oi') or 0):,}",
            "PE OI": f"{int(r.get('pe_oi') or 0):,}",
            "CE Δ": estimate_delta(strike, spot, True),
            "PE Δ": estimate_delta(strike, spot, False),
        })
        row_idx = len(table_rows) - 1

        if strike == atm:
            styles.append({
                "if": {"row_index": row_idx},
                "backgroundColor": "#1a3a5c",
                "border": "1px solid #00e5ff",
                "fontWeight": "bold",
            })
        if (r.get("ce_oi") or 0) == max_ce_oi and max_ce_oi > 0:
            styles.append({
                "if": {"row_index": row_idx, "column_id": "CE OI"},
                "backgroundColor": "#1a4a1a",
                "color": "#4caf50",
            })
        if (r.get("pe_oi") or 0) == max_pe_oi and max_pe_oi > 0:
            styles.append({
                "if": {"row_index": row_idx, "column_id": "PE OI"},
                "backgroundColor": "#4a1a1a",
                "color": "#ef5350",
            })

    return table_rows, styles


# ─────────────────────────── UI HELPERS ─────────────────────
_SIGNAL_BG = {
    "STRONG BUY": "#00c853",
    "WEAK BUY": "#00acc1",
    "NEUTRAL": "#616161",
    "WEAK SELL": "#ff6f00",
    "STRONG SELL": "#c62828",
}

_EMPTY_PLAN = {"strike": "-", "entry": "-", "sl": "-", "t1": "-", "t2": "-", "delta": "-", "oi": 0}


def _signal_badge(signal: str) -> dbc.Badge:
    return dbc.Badge(
        signal,
        style={
            "backgroundColor": _SIGNAL_BG.get(signal, "#616161"),
            "fontSize": "0.9rem",
            "padding": "5px 14px",
        },
    )


def _trade_card(plan: dict, side: str) -> dbc.Card:
    color = "#26a69a" if side == "CALL" else "#ef5350"
    icon = "📈" if side == "CALL" else "📉"
    oi_val = plan.get("oi", 0)
    oi_str = f"{oi_val:,}" if isinstance(oi_val, int) else str(oi_val)
    return dbc.Card(
        [
            dbc.CardHeader(
                html.Strong(f"{icon} {side} BUY — Strike {plan.get('strike', '-')}"),
                style={"color": color},
            ),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [html.Small("Entry"), html.H6(str(plan.get("entry", "-")), style={"color": color})],
                                xs=3,
                            ),
                            dbc.Col(
                                [html.Small("Stop Loss"), html.H6(str(plan.get("sl", "-")), style={"color": "#ef5350"})],
                                xs=3,
                            ),
                            dbc.Col(
                                [html.Small("Target 1"), html.H6(str(plan.get("t1", "-")), style={"color": "#26a69a"})],
                                xs=3,
                            ),
                            dbc.Col(
                                [html.Small("Target 2"), html.H6(str(plan.get("t2", "-")), style={"color": "#26a69a"})],
                                xs=3,
                            ),
                        ]
                    ),
                    html.Small(f"Δ {plan.get('delta', '-')}  |  OI {oi_str}", className="text-muted"),
                ]
            ),
        ],
        style={"backgroundColor": "#1a1a2e", "borderLeft": f"4px solid {color}"},
    )


# ─────────────────────────── APP LAYOUT ─────────────────────
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True,
    title="AI Trading Dashboard",
)
server = app.server  # required for gunicorn

_OC_COLUMNS = [
    {"name": "Strike", "id": "Strike"},
    {"name": "CE LTP", "id": "CE LTP"},
    {"name": "PE LTP", "id": "PE LTP"},
    {"name": "CE OI", "id": "CE OI"},
    {"name": "PE OI", "id": "PE OI"},
    {"name": "CE Δ", "id": "CE Δ"},
    {"name": "PE Δ", "id": "PE Δ"},
]

app.layout = dbc.Container(
    fluid=True,
    style={"backgroundColor": "#0d0d1a", "minHeight": "100vh", "paddingBottom": "40px"},
    children=[
        # ── Header ────────────────────────────────────────────
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.H4("🧠 AI Trading Dashboard", className="mb-0"),
                                    xs="auto",
                                ),
                                dbc.Col(
                                    html.Span("NIFTY · Live", style={"color": "#aaa"}),
                                    xs="auto",
                                    className="my-auto",
                                ),
                                dbc.Col(
                                    html.Div(id="header-signal"),
                                    xs="auto",
                                    className="my-auto",
                                ),
                                dbc.Col(
                                    dbc.Badge("◉ CONNECTING", id="status-badge", color="secondary"),
                                    xs="auto",
                                    className="my-auto ms-auto",
                                ),
                            ],
                            align="center",
                        )
                    ),
                    style={"backgroundColor": "#1a1a2e"},
                ),
                className="mb-3",
            ),
        ),

        # ── Stats Row ─────────────────────────────────────────
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.P("LTP", className="card-text text-muted mb-1",
                                       style={"fontSize": "0.72rem"}),
                                html.H4(id="stat-ltp", children="—",
                                        style={"color": "#00e5ff", "marginBottom": 0}),
                            ]
                        ),
                        style={"backgroundColor": "#1a1a2e", "border": "1px solid #333"},
                        className="text-center",
                    ),
                    xs=6, md=2, className="mb-2",
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.P("ATM Strike", className="card-text text-muted mb-1",
                                       style={"fontSize": "0.72rem"}),
                                html.H5(id="stat-atm", children="—",
                                        style={"color": "#f7b500", "marginBottom": 0}),
                            ]
                        ),
                        style={"backgroundColor": "#1a1a2e", "border": "1px solid #333"},
                        className="text-center",
                    ),
                    xs=6, md=2, className="mb-2",
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.P("PCR", className="card-text text-muted mb-1",
                                       style={"fontSize": "0.72rem"}),
                                html.H5(id="stat-pcr", children="—",
                                        style={"color": "#e040fb", "marginBottom": 0}),
                            ]
                        ),
                        style={"backgroundColor": "#1a1a2e", "border": "1px solid #333"},
                        className="text-center",
                    ),
                    xs=6, md=2, className="mb-2",
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.P("Trend", className="card-text text-muted mb-1",
                                       style={"fontSize": "0.72rem"}),
                                html.H5(id="stat-trend", children="—",
                                        style={"color": "#26a69a", "marginBottom": 0}),
                            ]
                        ),
                        style={"backgroundColor": "#1a1a2e", "border": "1px solid #333"},
                        className="text-center",
                    ),
                    xs=6, md=2, className="mb-2",
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.P("Signal", className="card-text text-muted mb-1",
                                       style={"fontSize": "0.72rem"}),
                                html.H5(id="stat-signal", children="—",
                                        style={"color": "#fff", "marginBottom": 0}),
                            ]
                        ),
                        style={"backgroundColor": "#1a1a2e", "border": "1px solid #333"},
                        className="text-center",
                    ),
                    xs=6, md=2, className="mb-2",
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.P("Confidence", className="card-text text-muted mb-1",
                                       style={"fontSize": "0.72rem"}),
                                html.H5(id="stat-conf", children="—%",
                                        style={"color": "#ff6b35", "marginBottom": 0}),
                            ]
                        ),
                        style={"backgroundColor": "#1a1a2e", "border": "1px solid #333"},
                        className="text-center",
                    ),
                    xs=6, md=2, className="mb-2",
                ),
            ],
            className="mb-3",
        ),

        # ── Chart + Trade Plans ───────────────────────────────
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                dbc.Row(
                                    [
                                        dbc.Col(html.Strong("Price Chart"), xs="auto"),
                                        dbc.Col(
                                            dbc.ButtonGroup(
                                                [
                                                    dbc.Button("Line", id="btn-line", n_clicks=0,
                                                               size="sm", color="primary", outline=True),
                                                    dbc.Button("Candle", id="btn-candle", n_clicks=0,
                                                               size="sm", color="primary", outline=True),
                                                ]
                                            ),
                                            xs="auto",
                                            className="ms-auto",
                                        ),
                                    ],
                                    align="center",
                                )
                            ),
                            dbc.CardBody(
                                dcc.Graph(
                                    id="price-chart",
                                    config={"displayModeBar": False},
                                    figure=_empty_figure("NIFTY Price"),
                                )
                            ),
                        ],
                        style={"backgroundColor": "#1a1a2e"},
                    ),
                    xs=12, lg=8, className="mb-3",
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(html.Strong("Trade Plans")),
                            dbc.CardBody(
                                [
                                    html.Div(id="call-trade-card", children=_trade_card(_EMPTY_PLAN, "CALL"),
                                             className="mb-3"),
                                    html.Div(id="put-trade-card", children=_trade_card(_EMPTY_PLAN, "PUT")),
                                ]
                            ),
                        ],
                        style={"backgroundColor": "#1a1a2e"},
                    ),
                    xs=12, lg=4, className="mb-3",
                ),
            ]
        ),

        # ── Option Chain Table ────────────────────────────────
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(html.Strong("Option Chain — NIFTY")),
                        dbc.CardBody(
                            dash_table.DataTable(
                                id="oc-table",
                                columns=_OC_COLUMNS,
                                page_size=15,
                                style_table={"overflowX": "auto"},
                                style_header={
                                    "backgroundColor": "#16213e",
                                    "color": "#aaa",
                                    "fontWeight": "bold",
                                    "border": "1px solid #333",
                                },
                                style_cell={
                                    "backgroundColor": "#0d0d1a",
                                    "color": "#e0e0e0",
                                    "border": "1px solid #222",
                                    "textAlign": "center",
                                    "padding": "8px",
                                },
                                style_data_conditional=[],
                            )
                        ),
                    ],
                    style={"backgroundColor": "#1a1a2e"},
                ),
                xs=12,
            )
        ),

        # ── Stores & Intervals ────────────────────────────────
        dcc.Store(id="history-store", data=[]),
        dcc.Store(id="chart-type-store", data="line"),
        dcc.Interval(id="ltp-tick", interval=LTP_INTERVAL_MS, n_intervals=0),
        dcc.Interval(id="oc-tick", interval=OC_INTERVAL_MS, n_intervals=0),
        dcc.Interval(id="chart-tick", interval=CHART_INTERVAL_MS, n_intervals=0),
    ],
)


# ─────────────────────────── CALLBACKS ──────────────────────

@app.callback(
    Output("chart-type-store", "data"),
    Input("btn-line", "n_clicks"),
    Input("btn-candle", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_chart_type(_line, _candle):
    triggered = ctx.triggered_id
    return "candlestick" if triggered == "btn-candle" else "line"


@app.callback(
    Output("stat-ltp", "children"),
    Output("status-badge", "children"),
    Output("status-badge", "color"),
    Output("history-store", "data"),
    Output("ltp-tick", "interval"),
    Input("ltp-tick", "n_intervals"),
    State("history-store", "data"),
    State("ltp-tick", "interval"),
    prevent_initial_call=False,
)
def update_ltp(_n, history, cur_interval):
    history = history or []
    ltp, err = fetch_ltp()
    if err:
        log.warning("LTP fetch failed: %s", err)
        return "ERROR", "◉ ERROR", "danger", history, _backoff(cur_interval, True, LTP_INTERVAL_MS)

    ts = datetime.now().strftime("%H:%M:%S")
    history.append({"time": ts, "price": ltp})
    history = history[-MAX_HISTORY:]
    return f"{ltp:,.2f}", "◉ LIVE", "success", history, LTP_INTERVAL_MS


@app.callback(
    Output("stat-atm", "children"),
    Output("stat-pcr", "children"),
    Output("stat-trend", "children"),
    Output("stat-signal", "children"),
    Output("stat-conf", "children"),
    Output("header-signal", "children"),
    Output("oc-table", "data"),
    Output("oc-table", "style_data_conditional"),
    Output("call-trade-card", "children"),
    Output("put-trade-card", "children"),
    Output("oc-tick", "interval"),
    Input("oc-tick", "n_intervals"),
    State("history-store", "data"),
    State("oc-tick", "interval"),
    prevent_initial_call=False,
)
def update_oc_and_signals(_n, history, cur_interval):
    history = history or []

    # Resolve spot price
    spot = history[-1]["price"] if history else None
    if spot is None:
        ltp, _ = fetch_ltp()
        spot = ltp

    rows, err = fetch_option_chain()

    if err and not rows:
        log.warning("Option chain failed: %s", err)
        badge = dbc.Badge("NEUTRAL", color="secondary")
        return (
            "—", "—", "—", "—", "—%",
            badge, [], [],
            _trade_card(_EMPTY_PLAN, "CALL"),
            _trade_card(_EMPTY_PLAN, "PUT"),
            _backoff(cur_interval, True, OC_INTERVAL_MS),
        )

    pcr = calc_pcr(rows)
    sig_data = calc_signal(history, pcr)
    signal = sig_data["signal"]

    atm_str = str(int(round(spot / 50) * 50)) if spot else "—"

    table_rows, styles = build_oc_table_data(rows, spot or 0)

    call_info = select_smart_strike(rows, spot or 0, "CE")
    put_info = select_smart_strike(rows, spot or 0, "PE")
    call_plan = build_trade_plan(call_info, "CALL")
    put_plan = build_trade_plan(put_info, "PUT")

    header_badge = dbc.Badge(
        f"{signal}  |  {sig_data['entry']}",
        style={
            "backgroundColor": _SIGNAL_BG.get(signal, "#616161"),
            "fontSize": "0.85rem",
            "padding": "5px 12px",
        },
    )

    return (
        atm_str,
        str(pcr),
        sig_data["trend"],
        signal,
        f"{sig_data['confidence']}%",
        header_badge,
        table_rows,
        styles,
        _trade_card(call_plan, "CALL"),
        _trade_card(put_plan, "PUT"),
        OC_INTERVAL_MS,
    )


@app.callback(
    Output("price-chart", "figure"),
    Input("chart-tick", "n_intervals"),
    Input("ltp-tick", "n_intervals"),
    Input("chart-type-store", "data"),
    State("history-store", "data"),
    prevent_initial_call=False,
)
def update_chart(_chart_n, _ltp_n, chart_type, history):
    return build_price_chart(history or [], chart_type or "line")


# ─────────────────────────── ENTRY POINT ────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
