"""
Production-ready Dash AI Trading Dashboard — Dhan API
=======================================================
Features
--------
* Live NIFTY LTP via requests.Session (1-second refresh)
* Option chain: strike, CE/PE LTP, CE/PE OI, estimated deltas
  - Expiry and option-chain caching
  - ATM detection, PCR calculation
  - Smart strike selection (ATM proximity + delta 0.3-0.6 + high OI)
* Trade plan generator: Entry, SL, T1, T2
* AI signal: EMA21, VWAP, Momentum → STRONG/WEAK BUY/SELL/NEUTRAL
  - Entry signals: CALL BUY / PUT BUY
* Chart: toggle candlestick/line, EMA 9/21/50, VWAP, prev high/low,
  LTP line, tick-volume
* Dark Cyborg theme
* Production safe: debug=False, host 0.0.0.0, exponential backoff,
  no dash.Patch, always-valid Plotly figures
"""

import os
import time
from datetime import datetime

import pandas as pd
import plotly.graph_objs as go
import requests
from dash import Dash, Input, Output, State, dash_table, dcc, html, no_update
import dash_bootstrap_components as dbc

# ---------------------------------------------------------------------------
# ENV / CONSTANTS
# ---------------------------------------------------------------------------
CLIENT_ID = os.getenv("CLIENT_ID", "")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "")
PORT = int(os.environ.get("PORT", 8050))

BASE_URL = "https://api.dhan.co/v2"
LTP_URL = f"{BASE_URL}/marketfeed/ltp"
EXPIRY_URL = f"{BASE_URL}/optionChain/expiryList"
OC_URL = f"{BASE_URL}/optionChain"

NIFTY_ID = 13
NIFTY_SEG = "IDX_I"

LTP_INTERVAL_MS = 1000       # 1 s
OC_INTERVAL_MS = 8000        # 8 s
REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", 4))
MAX_CANDLES = 150
OC_CACHE_TTL = 15            # seconds
EXPIRY_CACHE_TTL = 300       # seconds
BACKOFF_CAP_MS = 30_000      # 30 s

STRIKE_STEP = 50             # NIFTY strike distance
DELTA_LO, DELTA_HI = 0.30, 0.60

# ---------------------------------------------------------------------------
# SHARED HTTP SESSION (connection pooling)
# ---------------------------------------------------------------------------
_session = requests.Session()
_session.headers.update(
    {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json",
    }
)

# ---------------------------------------------------------------------------
# IN-MEMORY CACHES
# ---------------------------------------------------------------------------
_expiry_cache: dict = {"code": None, "ts": 0.0}
_oc_cache: dict = {"rows": [], "spot": 0.0, "ts": 0.0}


# ---------------------------------------------------------------------------
# HELPERS: API
# ---------------------------------------------------------------------------

def _backoff(prev_ms: int, failed: bool) -> int:
    """Exponential backoff capped at BACKOFF_CAP_MS."""
    if not failed:
        return LTP_INTERVAL_MS
    return min(prev_ms * 2, BACKOFF_CAP_MS)


def _safe_float(val, default=0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _extract_side_price(side: dict) -> float:
    if not isinstance(side, dict):
        return 0.0
    for key in ("ltp", "lastPrice", "LTP", "last_price", "price"):
        v = side.get(key)
        if v is not None:
            return _safe_float(v)
    return 0.0


def _extract_side_oi(side: dict) -> float:
    if not isinstance(side, dict):
        return 0.0
    for key in ("oi", "openInterest", "OI", "open_interest"):
        v = side.get(key)
        if v is not None:
            return _safe_float(v)
    return 0.0


def _estimate_delta(strike: float, spot: float, is_call: bool) -> float:
    """Very rough delta proxy using moneyness (no vol/time inputs)."""
    if spot <= 0:
        return 0.0
    moneyness = (spot - strike) / spot
    raw = 0.5 + moneyness * 5.0
    raw = max(0.01, min(0.99, raw))
    return round(raw if is_call else (1.0 - raw), 2)


# ---------------------------------------------------------------------------
# FETCH: LTP
# ---------------------------------------------------------------------------

def fetch_ltp() -> tuple[float | None, str | None]:
    try:
        resp = _session.post(
            LTP_URL,
            json={"NSE_INDEX": [NIFTY_ID]},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        price = None
        if isinstance(data, list) and data:
            price = data[0].get("ltp") or data[0].get("lastPrice")
        elif isinstance(data, dict):
            seg_val = next(iter(data.values()), {})
            if isinstance(seg_val, list) and seg_val:
                price = seg_val[0].get("ltp") or seg_val[0].get("lastPrice")
            elif isinstance(seg_val, dict):
                price = seg_val.get("ltp") or seg_val.get("lastPrice")
        if price is None:
            return None, "LTP: empty response"
        return float(price), None
    except Exception as exc:
        return None, f"LTP: {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# FETCH: EXPIRY
# ---------------------------------------------------------------------------

def fetch_expiry() -> tuple[str | None, str | None]:
    now = time.time()
    if _expiry_cache["code"] and now - _expiry_cache["ts"] < EXPIRY_CACHE_TTL:
        return _expiry_cache["code"], None
    try:
        resp = _session.post(
            EXPIRY_URL,
            json={"UnderlyingScrip": NIFTY_ID, "UnderlyingSeg": NIFTY_SEG},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json().get("data") or []
        if not data:
            return None, "Expiry: empty list"
        first = data[0]
        code = first.get("expiryCode") if isinstance(first, dict) else first
        _expiry_cache["code"] = code
        _expiry_cache["ts"] = now
        return code, None
    except Exception as exc:
        return None, f"Expiry: {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# FETCH: OPTION CHAIN
# ---------------------------------------------------------------------------

_OC_FALLBACK = [
    {"Strike": "-", "CE LTP": "-", "PE LTP": "-", "CE OI": "-", "PE OI": "-",
     "CE Δ": "-", "PE Δ": "-"}
    for _ in range(10)
]


def fetch_option_chain() -> tuple[list[dict], float, str | None]:
    """Return (rows, spot_price, error_or_None)."""
    now = time.time()
    if _oc_cache["rows"] and now - _oc_cache["ts"] < OC_CACHE_TTL:
        return _oc_cache["rows"], _oc_cache["spot"], None

    expiry_code, err = fetch_expiry()
    if err:
        return _OC_FALLBACK, 0.0, err

    try:
        resp = _session.post(
            OC_URL,
            json={
                "UnderlyingScrip": NIFTY_ID,
                "UnderlyingSeg": NIFTY_SEG,
                "ExpiryCode": expiry_code,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data") or []
        if not data:
            return _OC_FALLBACK, 0.0, "OC: empty data"

        # detect spot from first record or separate key
        spot = _safe_float(
            payload.get("underlying_ltp")
            or payload.get("underlyingValue")
            or payload.get("spot")
        )

        rows = []
        for item in data:
            strike = _safe_float(item.get("strikePrice") or item.get("strike_price") or 0)
            ce = item.get("CE") or item.get("ce") or {}
            pe = item.get("PE") or item.get("pe") or {}
            ce_ltp = _extract_side_price(ce)
            pe_ltp = _extract_side_price(pe)
            ce_oi = _extract_side_oi(ce)
            pe_oi = _extract_side_oi(pe)
            # if spot still 0 try last_price from response
            if spot == 0.0:
                spot = _safe_float(item.get("underlyingValue") or item.get("last_price") or 0)
            rows.append(
                {
                    "Strike": strike,
                    "CE LTP": round(ce_ltp, 2) if ce_ltp else "-",
                    "PE LTP": round(pe_ltp, 2) if pe_ltp else "-",
                    "CE OI": int(ce_oi) if ce_oi else "-",
                    "PE OI": int(pe_oi) if pe_oi else "-",
                    "CE Δ": _estimate_delta(strike, spot, is_call=True),
                    "PE Δ": _estimate_delta(strike, spot, is_call=False),
                    "_ce_ltp": ce_ltp,
                    "_pe_ltp": pe_ltp,
                    "_ce_oi": ce_oi,
                    "_pe_oi": pe_oi,
                }
            )

        _oc_cache["rows"] = rows
        _oc_cache["spot"] = spot
        _oc_cache["ts"] = now
        return rows, spot, None
    except Exception as exc:
        return _OC_FALLBACK, 0.0, f"OC: {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# ATM / SMART STRIKE
# ---------------------------------------------------------------------------

def find_atm(rows: list[dict], spot: float) -> float | None:
    if not rows or spot <= 0:
        return None
    rounded = round(spot / STRIKE_STEP) * STRIKE_STEP
    strikes = [r["Strike"] for r in rows if isinstance(r["Strike"], (int, float))]
    if not strikes:
        return None
    return min(strikes, key=lambda s: abs(s - rounded))


def select_smart_strikes(rows: list[dict], spot: float) -> tuple[dict | None, dict | None]:
    """Return (best_ce_row, best_pe_row) using delta range + OI."""
    if not rows or spot <= 0:
        return None, None

    atm = find_atm(rows, spot)
    if atm is None:
        return None, None

    window = 5 * STRIKE_STEP

    def score(row, is_call: bool) -> float:
        strike = row.get("Strike")
        if not isinstance(strike, (int, float)):
            return -1.0
        if abs(strike - atm) > window:
            return -1.0
        delta = row.get("CE Δ" if is_call else "PE Δ", 0)
        if not (DELTA_LO <= abs(_safe_float(delta)) <= DELTA_HI):
            return -1.0
        oi = _safe_float(row.get("_ce_oi" if is_call else "_pe_oi", 0))
        ltp = _safe_float(row.get("_ce_ltp" if is_call else "_pe_ltp", 0))
        return oi * 0.6 + ltp * 0.4

    valid_rows = [r for r in rows if isinstance(r.get("Strike"), (int, float))]
    best_ce = max(valid_rows, key=lambda r: score(r, True), default=None)
    best_pe = max(valid_rows, key=lambda r: score(r, False), default=None)

    if best_ce and score(best_ce, True) <= 0:
        best_ce = None
    if best_pe and score(best_pe, False) <= 0:
        best_pe = None

    return best_ce, best_pe


def calc_pcr(rows: list[dict]) -> float:
    total_ce_oi = sum(_safe_float(r.get("_ce_oi", 0)) for r in rows)
    total_pe_oi = sum(_safe_float(r.get("_pe_oi", 0)) for r in rows)
    if total_ce_oi == 0:
        return 0.0
    return round(total_pe_oi / total_ce_oi, 3)


# ---------------------------------------------------------------------------
# AI SIGNAL ENGINE
# ---------------------------------------------------------------------------

def _ema(prices: list[float], period: int) -> list[float]:
    if len(prices) < period:
        return [prices[-1]] * len(prices) if prices else []
    k = 2 / (period + 1)
    result = [sum(prices[:period]) / period]
    for p in prices[period:]:
        result.append(p * k + result[-1] * (1 - k))
    return [result[0]] * (period - 1) + result


def _vwap(prices: list[float], volumes: list[float]) -> list[float]:
    cum_pv, cum_v = 0.0, 0.0
    out = []
    for p, v in zip(prices, volumes):
        cum_pv += p * v
        cum_v += v
        out.append(cum_pv / cum_v if cum_v else p)
    return out


def compute_signals(history: list[dict]) -> dict:
    """
    history: list of {"time": str, "price": float, "volume": float}

    Returns dict with keys:
      ema9, ema21, ema50, vwap, signal_label, signal_strength,
      entry_signal, confidence, trend
    """
    default = {
        "ema9": [], "ema21": [], "ema50": [], "vwap": [],
        "signal_label": "NEUTRAL", "signal_strength": "WEAK",
        "entry_signal": "—", "confidence": 0, "trend": "SIDEWAYS",
    }
    if len(history) < 5:
        return default

    prices = [h["price"] for h in history]
    volumes = [h.get("volume", 1.0) for h in history]

    ema9 = _ema(prices, 9)
    ema21 = _ema(prices, 21)
    ema50 = _ema(prices, 50)
    vwap_line = _vwap(prices, volumes)

    ltp = prices[-1]
    e21 = ema21[-1]
    vwap_now = vwap_line[-1]

    # momentum: price change over last 5 candles
    mom = ltp - prices[-min(5, len(prices))]
    mom_score = 1 if mom > 0 else (-1 if mom < 0 else 0)

    # trend
    if len(ema50) >= 2 and ema50[-1] > ema50[-2]:
        trend = "BULLISH"
    elif len(ema50) >= 2 and ema50[-1] < ema50[-2]:
        trend = "BEARISH"
    else:
        trend = "SIDEWAYS"

    # scoring
    bull_pts = 0
    bear_pts = 0
    if ltp > e21:
        bull_pts += 1
    else:
        bear_pts += 1
    if ltp > vwap_now:
        bull_pts += 1
    else:
        bear_pts += 1
    if mom_score > 0:
        bull_pts += 1
    elif mom_score < 0:
        bear_pts += 1

    total = bull_pts + bear_pts
    diff = bull_pts - bear_pts

    if diff >= 2:
        signal_label = "BUY"
        entry_signal = "CALL BUY"
    elif diff <= -2:
        signal_label = "SELL"
        entry_signal = "PUT BUY"
    else:
        signal_label = "NEUTRAL"
        entry_signal = "—"

    strength = "STRONG" if abs(diff) == 3 else ("WEAK" if abs(diff) == 1 else "MODERATE")
    confidence = int((abs(diff) / max(total, 1)) * 100)

    return {
        "ema9": ema9,
        "ema21": ema21,
        "ema50": ema50,
        "vwap": vwap_line,
        "signal_label": signal_label,
        "signal_strength": strength,
        "entry_signal": entry_signal,
        "confidence": confidence,
        "trend": trend,
    }


# ---------------------------------------------------------------------------
# TRADE PLAN
# ---------------------------------------------------------------------------

def make_trade_plan(
    history: list[dict],
    ce_row: dict | None,
    pe_row: dict | None,
    entry_signal: str,
) -> dict:
    if not history or len(history) < 3:
        return {}

    prices = [h["price"] for h in history]
    recent = prices[-3:]
    prev_low = min(recent)
    prev_high = max(recent)

    plan = {}
    risk_reward = 2.0

    if entry_signal == "CALL BUY" and ce_row:
        entry = _safe_float(ce_row.get("_ce_ltp", 0))
        sl_pts = _safe_float(prices[-1]) - prev_low
        sl = max(entry - sl_pts, entry * 0.85)
        t1 = entry + sl_pts * risk_reward
        t2 = entry + sl_pts * risk_reward * 2
        plan = {
            "side": "CALL BUY",
            "strike": ce_row.get("Strike"),
            "entry": round(entry, 2),
            "sl": round(sl, 2),
            "t1": round(t1, 2),
            "t2": round(t2, 2),
        }

    elif entry_signal == "PUT BUY" and pe_row:
        entry = _safe_float(pe_row.get("_pe_ltp", 0))
        sl_pts = prev_high - _safe_float(prices[-1])
        sl = max(entry - sl_pts, entry * 0.85)
        t1 = entry + sl_pts * risk_reward
        t2 = entry + sl_pts * risk_reward * 2
        plan = {
            "side": "PUT BUY",
            "strike": pe_row.get("Strike"),
            "entry": round(entry, 2),
            "sl": round(sl, 2),
            "t1": round(t1, 2),
            "t2": round(t2, 2),
        }

    return plan


# ---------------------------------------------------------------------------
# CHART BUILDER
# ---------------------------------------------------------------------------

def build_chart(history: list[dict], chart_type: str, signals: dict) -> go.Figure:
    """Build LTP chart with EMA 9/21/50, VWAP, prev high/low, LTP line, volume."""
    fig = go.Figure()
    layout_kwargs = dict(
        template="plotly_dark",
        paper_bgcolor="#060606",
        plot_bgcolor="#0d0d0d",
        margin=dict(l=50, r=20, t=40, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#222"),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, showticklabels=False),
    )

    if not history:
        fig.update_layout(**layout_kwargs)
        return fig

    df = pd.DataFrame(history)
    times = df["time"].tolist()
    prices = df["price"].tolist()
    volumes = df.get("volume", pd.Series([1.0] * len(df))).tolist()

    # — price trace
    if chart_type == "candlestick" and len(df) >= 2:
        # simulate OHLC from 1-min ticks (group by minute index)
        df["open"] = df["price"].shift(1).fillna(df["price"])
        df["high"] = df[["price", "open"]].max(axis=1)
        df["low"] = df[["price", "open"]].min(axis=1)
        fig.add_trace(
            go.Candlestick(
                x=times,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=prices,
                name="Price",
                increasing_line_color="#00e676",
                decreasing_line_color="#ff1744",
            )
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=times, y=prices, mode="lines",
                name="LTP",
                line=dict(color="#00bcd4", width=1.5),
            )
        )

    # — EMA / VWAP overlays
    ema9 = signals.get("ema9", [])
    ema21 = signals.get("ema21", [])
    ema50 = signals.get("ema50", [])
    vwap_line = signals.get("vwap", [])

    def _overlay(y_vals, name, color, dash="solid"):
        if len(y_vals) == len(times):
            fig.add_trace(
                go.Scatter(x=times, y=y_vals, mode="lines",
                           name=name, line=dict(color=color, width=1, dash=dash))
            )

    _overlay(ema9, "EMA9", "#ffeb3b")
    _overlay(ema21, "EMA21", "#ff9800")
    _overlay(ema50, "EMA50", "#e91e63")
    _overlay(vwap_line, "VWAP", "#00e5ff", dash="dot")

    # — previous high / low lines
    if len(prices) >= 2:
        prev_hi = max(prices[:-1])
        prev_lo = min(prices[:-1])
        for val, color, label in [
            (prev_hi, "#76ff03", "Prev High"),
            (prev_lo, "#ff3d00", "Prev Low"),
        ]:
            fig.add_hline(
                y=val, line_color=color, line_dash="dash", line_width=1,
                annotation_text=label,
                annotation_font_color=color,
                annotation_position="right",
            )

    # — LTP reference line
    fig.add_hline(
        y=prices[-1], line_color="#ffffff", line_dash="dot", line_width=1,
        annotation_text=f"LTP {prices[-1]:.2f}",
        annotation_font_color="#ffffff",
        annotation_position="right",
    )

    # — volume bars (secondary axis)
    fig.add_trace(
        go.Bar(
            x=times, y=volumes,
            name="Volume", opacity=0.25,
            marker_color="#607d8b",
            yaxis="y2",
        )
    )

    fig.update_layout(**layout_kwargs)
    return fig


# ---------------------------------------------------------------------------
# DASH APP + LAYOUT
# ---------------------------------------------------------------------------
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True,
)
server = app.server  # expose for gunicorn


def _badge(text: str, color: str) -> dbc.Badge:
    return dbc.Badge(text, color=color, className="ms-2 fs-6")


def _stat_card(title: str, value_id: str, badge_color: str = "secondary") -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            [
                html.Small(title, className="text-muted"),
                html.H5(id=value_id, children="—", className="mb-0 mt-1"),
            ]
        ),
        className="text-center",
    )


def _trade_card(side: str, id_prefix: str) -> dbc.Card:
    color = "success" if side == "CALL" else "danger"
    return dbc.Card(
        [
            dbc.CardHeader(
                f"{'📈' if side == 'CALL' else '📉'} {side} BUY",
                className=f"text-{color} fw-bold",
            ),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(html.Small("Strike")),
                            dbc.Col(html.Strong(id=f"{id_prefix}-strike", children="—")),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(html.Small("Entry")),
                            dbc.Col(html.Strong(id=f"{id_prefix}-entry", children="—")),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(html.Small("SL")),
                            dbc.Col(
                                html.Strong(id=f"{id_prefix}-sl", children="—",
                                            className="text-danger")
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(html.Small("T1")),
                            dbc.Col(
                                html.Strong(id=f"{id_prefix}-t1", children="—",
                                            className="text-success")
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(html.Small("T2")),
                            dbc.Col(
                                html.Strong(id=f"{id_prefix}-t2", children="—",
                                            className="text-success")
                            ),
                        ]
                    ),
                ]
            ),
        ],
        outline=True,
        color=color,
    )


app.layout = dbc.Container(
    fluid=True,
    children=[
        # ── Hidden stores / intervals ──────────────────────────────────────
        dcc.Store(id="history-store", data=[]),
        dcc.Store(id="oc-store", data=[]),
        dcc.Store(id="chart-type-store", data="line"),
        dcc.Interval(id="ltp-interval", interval=LTP_INTERVAL_MS, n_intervals=0),
        dcc.Interval(id="oc-interval", interval=OC_INTERVAL_MS, n_intervals=0),

        # ── HEADER ─────────────────────────────────────────────────────────
        dbc.Row(
            dbc.Col(
                dbc.Navbar(
                    dbc.Container(
                        [
                            html.Span("🚀 AI Trading Dashboard — NIFTY",
                                      className="navbar-brand fw-bold fs-5"),
                            dbc.Badge(id="signal-badge", children="NEUTRAL",
                                      color="secondary", className="fs-6 me-2"),
                            dbc.Badge(id="status-badge", children="Connecting…",
                                      color="warning", className="fs-6"),
                        ],
                        fluid=True,
                    ),
                    color="dark",
                    dark=True,
                    className="mb-3",
                ),
            )
        ),

        # ── TOP ROW: LTP + timestamp + chart toggle ────────────────────────
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Small("NIFTY LTP", className="text-muted"),
                                html.H2(id="ltp-display", children="—",
                                        className="text-info fw-bold mb-0"),
                                html.Small(id="ts-display", children="—",
                                           className="text-muted"),
                            ]
                        )
                    ),
                    md=4,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Small("Chart Type", className="text-muted d-block"),
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button("Line", id="btn-line",
                                                   color="info", outline=False, size="sm"),
                                        dbc.Button("Candlestick", id="btn-candle",
                                                   color="secondary", outline=True, size="sm"),
                                    ]
                                ),
                            ]
                        )
                    ),
                    md=4,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Small("Entry Signal", className="text-muted d-block"),
                                html.H4(id="entry-signal-display", children="—",
                                        className="fw-bold mb-0"),
                            ]
                        )
                    ),
                    md=4,
                ),
            ],
            className="mb-3",
        ),

        # ── STATS CARDS ────────────────────────────────────────────────────
        dbc.Row(
            [
                dbc.Col(_stat_card("ATM Strike", "stat-atm"), md=2, sm=4, xs=6),
                dbc.Col(_stat_card("PCR", "stat-pcr"), md=2, sm=4, xs=6),
                dbc.Col(_stat_card("Trend", "stat-trend"), md=2, sm=4, xs=6),
                dbc.Col(_stat_card("Signal", "stat-signal"), md=2, sm=4, xs=6),
                dbc.Col(_stat_card("Strength", "stat-strength"), md=2, sm=4, xs=6),
                dbc.Col(_stat_card("Confidence", "stat-confidence"), md=2, sm=4, xs=6),
            ],
            className="mb-3",
        ),

        # ── MAIN CHART ─────────────────────────────────────────────────────
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        dcc.Graph(id="main-chart", style={"height": "380px"})
                    )
                )
            ),
            className="mb-3",
        ),

        # ── OPTION CHAIN TABLE ─────────────────────────────────────────────
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader("📊 Option Chain"),
                        dbc.CardBody(
                            dash_table.DataTable(
                                id="oc-table",
                                columns=[
                                    {"name": c, "id": c}
                                    for c in ["Strike", "CE LTP", "CE OI",
                                              "CE Δ", "PE Δ", "PE OI", "PE LTP"]
                                ],
                                page_size=20,
                                style_table={"overflowX": "auto"},
                                style_cell={
                                    "backgroundColor": "#111",
                                    "color": "#eee",
                                    "textAlign": "center",
                                    "padding": "4px 8px",
                                    "fontSize": "13px",
                                    "border": "1px solid #333",
                                },
                                style_header={
                                    "backgroundColor": "#222",
                                    "fontWeight": "bold",
                                    "color": "#fff",
                                },
                                style_data_conditional=[],
                            )
                        ),
                    ]
                )
            ),
            className="mb-3",
        ),

        # ── TRADE CARDS ────────────────────────────────────────────────────
        dbc.Row(
            [
                dbc.Col(_trade_card("CALL", "call"), md=6),
                dbc.Col(_trade_card("PUT", "put"), md=6),
            ],
            className="mb-4",
        ),
    ],
)


# ---------------------------------------------------------------------------
# CALLBACKS
# ---------------------------------------------------------------------------

@app.callback(
    Output("ltp-display", "children"),
    Output("ts-display", "children"),
    Output("status-badge", "children"),
    Output("status-badge", "color"),
    Output("main-chart", "figure"),
    Output("history-store", "data"),
    Output("ltp-interval", "interval"),
    Output("stat-atm", "children"),
    Output("stat-pcr", "children"),
    Output("stat-trend", "children"),
    Output("stat-signal", "children"),
    Output("stat-strength", "children"),
    Output("stat-confidence", "children"),
    Output("signal-badge", "children"),
    Output("signal-badge", "color"),
    Output("entry-signal-display", "children"),
    # CALL trade card
    Output("call-strike", "children"),
    Output("call-entry", "children"),
    Output("call-sl", "children"),
    Output("call-t1", "children"),
    Output("call-t2", "children"),
    # PUT trade card
    Output("put-strike", "children"),
    Output("put-entry", "children"),
    Output("put-sl", "children"),
    Output("put-t1", "children"),
    Output("put-t2", "children"),
    Input("ltp-interval", "n_intervals"),
    State("history-store", "data"),
    State("ltp-interval", "interval"),
    State("oc-store", "data"),
    State("chart-type-store", "data"),
    prevent_initial_call=False,
)
def update_ltp(_n, history, cur_interval, oc_rows, chart_type):
    history = history or []
    oc_rows = oc_rows or []
    chart_type = chart_type or "line"

    ltp, err = fetch_ltp()
    if err:
        empty_fig = go.Figure(
            layout=go.Layout(template="plotly_dark", paper_bgcolor="#060606",
                             plot_bgcolor="#0d0d0d")
        )
        new_int = _backoff(cur_interval, failed=True)
        no_val = "—"
        return (
            no_val, no_val, err, "danger", empty_fig, history, new_int,
            no_val, no_val, no_val, no_val, no_val, no_val,
            "ERROR", "danger", no_val,
            no_val, no_val, no_val, no_val, no_val,
            no_val, no_val, no_val, no_val, no_val,
        )

    ts = datetime.now().strftime("%H:%M:%S")
    history.append({"time": ts, "price": ltp, "volume": 1.0})
    history = history[-MAX_CANDLES:]

    # signals
    signals = compute_signals(history)
    sig_label = signals["signal_label"]
    sig_strength = signals["signal_strength"]
    entry_signal = signals["entry_signal"]
    confidence = signals["confidence"]
    trend = signals["trend"]

    sig_color = (
        "success" if sig_label == "BUY"
        else "danger" if sig_label == "SELL"
        else "secondary"
    )

    entry_color_map = {"CALL BUY": "text-success", "PUT BUY": "text-danger"}
    entry_class = entry_color_map.get(entry_signal, "text-white")
    entry_display = html.Span(entry_signal, className=entry_class)

    # build chart
    fig = build_chart(history, chart_type, signals)

    # option chain stats
    if oc_rows and isinstance(oc_rows[0], dict) and oc_rows[0].get("Strike") != "-":
        spot_from_oc = _oc_cache.get("spot", 0.0) or ltp
        atm = find_atm(oc_rows, spot_from_oc or ltp)
        pcr = calc_pcr(oc_rows)
        ce_row, pe_row = select_smart_strikes(oc_rows, spot_from_oc or ltp)
    else:
        atm = round(ltp / STRIKE_STEP) * STRIKE_STEP
        pcr = 0.0
        ce_row, pe_row = None, None

    plan = make_trade_plan(history, ce_row, pe_row, entry_signal)

    def _p(key): return str(plan.get(key, "—"))

    ce_strike = str(ce_row["Strike"]) if ce_row else "—"
    pe_strike = str(pe_row["Strike"]) if pe_row else "—"

    if entry_signal == "CALL BUY":
        call_strike = _p("strike") if plan else ce_strike
        call_entry = _p("entry")
        call_sl = _p("sl")
        call_t1 = _p("t1")
        call_t2 = _p("t2")
    else:
        call_strike, call_entry, call_sl, call_t1, call_t2 = ce_strike, "—", "—", "—", "—"

    if entry_signal == "PUT BUY":
        put_strike = _p("strike") if plan else pe_strike
        put_entry = _p("entry")
        put_sl = _p("sl")
        put_t1 = _p("t1")
        put_t2 = _p("t2")
    else:
        put_strike, put_entry, put_sl, put_t1, put_t2 = pe_strike, "—", "—", "—", "—"

    return (
        f"{ltp:.2f}", ts, "LIVE ●", "success", fig, history, LTP_INTERVAL_MS,
        str(atm), str(pcr), trend,
        f"{sig_strength} {sig_label}", sig_strength, f"{confidence}%",
        f"{sig_strength} {sig_label}", sig_color, entry_display,
        call_strike, call_entry, call_sl, call_t1, call_t2,
        put_strike, put_entry, put_sl, put_t1, put_t2,
    )


@app.callback(
    Output("oc-store", "data"),
    Output("oc-table", "data"),
    Output("oc-table", "style_data_conditional"),
    Input("oc-interval", "n_intervals"),
    State("history-store", "data"),
    prevent_initial_call=False,
)
def update_option_chain(_n, history):
    rows, spot, err = fetch_option_chain()
    if err or not rows:
        return [], _OC_FALLBACK, []

    # use live ltp if spot unavailable
    if not spot and history:
        spot = history[-1].get("price", 0.0) if history else 0.0

    atm = find_atm(rows, spot) if spot else None

    # highest OI strikes
    try:
        max_ce_oi_strike = max(
            (r for r in rows if isinstance(r.get("_ce_oi"), (int, float))),
            key=lambda r: r["_ce_oi"],
            default=None,
        )
        max_pe_oi_strike = max(
            (r for r in rows if isinstance(r.get("_pe_oi"), (int, float))),
            key=lambda r: r["_pe_oi"],
            default=None,
        )
    except Exception:
        max_ce_oi_strike = max_pe_oi_strike = None

    # build display rows (hide internal keys)
    display_cols = ["Strike", "CE LTP", "CE OI", "CE Δ", "PE Δ", "PE OI", "PE LTP"]
    display_rows = []
    for r in rows:
        row = {k: r.get(k, "—") for k in display_cols}
        # rename keys
        row["CE OI"] = r.get("CE OI", "—")
        row["PE OI"] = r.get("PE OI", "—")
        display_rows.append(row)

    # conditional styles
    styles = []
    if atm is not None:
        styles.append({
            "if": {"filter_query": f'{{Strike}} = {atm}'},
            "backgroundColor": "#1a3a1a",
            "color": "#00e676",
            "fontWeight": "bold",
        })
    if max_ce_oi_strike:
        styles.append({
            "if": {
                "filter_query": f'{{Strike}} = {max_ce_oi_strike["Strike"]}',
                "column_id": "CE OI",
            },
            "backgroundColor": "#1a2a3a",
            "color": "#00bcd4",
        })
    if max_pe_oi_strike:
        styles.append({
            "if": {
                "filter_query": f'{{Strike}} = {max_pe_oi_strike["Strike"]}',
                "column_id": "PE OI",
            },
            "backgroundColor": "#3a1a1a",
            "color": "#ff7043",
        })

    return rows, display_rows, styles


@app.callback(
    Output("chart-type-store", "data"),
    Output("btn-line", "color"),
    Output("btn-line", "outline"),
    Output("btn-candle", "color"),
    Output("btn-candle", "outline"),
    Input("btn-line", "n_clicks"),
    Input("btn-candle", "n_clicks"),
    State("chart-type-store", "data"),
    prevent_initial_call=True,
)
def toggle_chart(n_line, n_candle, current):
    from dash import ctx
    triggered = ctx.triggered_id
    if triggered == "btn-candle":
        return "candlestick", "secondary", True, "info", False
    return "line", "info", False, "secondary", True


# ---------------------------------------------------------------------------
# RUN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
    )
