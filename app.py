import os
import time
from datetime import datetime
import requests
import pandas as pd
import plotly.graph_objs as go
from dash import Dash, html, dcc, dash_table, Input, Output, State, no_update
import dash_bootstrap_components as dbc

# ---------- ENV ----------
CLIENT_ID = os.getenv("CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
PORT = int(os.environ.get("PORT", 3000))

# ---------- SESSION ----------
SESSION = requests.Session()
SESSION.headers.update(
    {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json",
    }
)

# ---------- API ----------
LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
EXPIRY_URL = "https://api.dhan.co/v2/optionChain/expiryList"
OPTION_CHAIN_URL = "https://api.dhan.co/v2/optionChain"
UNDERLYINGS = {"NIFTY": {"id": 13, "segment": "IDX_I"}}

# ---------- SETTINGS ----------
LTP_INTERVAL_MS = 1000
OC_INTERVAL_MS = 8000
REQUEST_TIMEOUT = 3
MAX_POINTS = 600
OC_CACHE_TTL = 15
EXPIRY_CACHE_TTL = 300
BACKOFF_CAP_MS = 30000
MAX_CANDLES = 200

# ---------- CACHE ----------
option_cache = {"data": [], "time": 0}
expiry_cache = {"code": None, "time": 0}

# ---------- HELPERS ----------
def safe_number(val):
    try:
        return float(val)
    except Exception:
        return None


def safe_price(value_dict: dict):
    if not value_dict:
        return None
    for key in ("ltp", "lastPrice", "LTP", "price"):
        val = value_dict.get(key)
        if val is not None:
            v = safe_number(val)
            if v is not None:
                return v
    return None


def exponential_backoff(current_ms, failed):
    if not failed:
        return LTP_INTERVAL_MS
    return min(current_ms * 2, BACKOFF_CAP_MS)


def cached_data(cache, ttl):
    now = time.time()
    if cache["data"] and now - cache["time"] < ttl:
        return cache["data"]
    return None


def update_cache(cache, data):
    cache["data"] = data
    cache["time"] = time.time()


def post_json(url, payload):
    try:
        resp = SESSION.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json(), None
    except Exception as e:
        return None, f"{url.split('/')[-1]} error: {type(e).__name__}: {e}"


# ---------- API CALLS ----------
def fetch_ltp():
    payload = {"NSE_INDEX": [UNDERLYINGS["NIFTY"]["id"]]}
    data, err = post_json(LTP_URL, payload)
    if err or not data:
        return None, err or "Empty LTP response"
    try:
        arr = data.get("data") or []
        if not arr:
            return None, "LTP response missing data"
        price = (
            safe_number(arr[0].get("lastPrice"))
            or safe_number(arr[0].get("ltp"))
            or safe_number(arr[0].get("price"))
        )
        if price is None:
            return None, "LTP price missing"
        return price, None
    except Exception as e:
        return None, f"LTP parse error: {type(e).__name__}: {e}"


def fetch_expiry():
    cached = cached_data(expiry_cache, EXPIRY_CACHE_TTL)
    if cached:
        return cached, None
    payload = {
        "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
        "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
    }
    data, err = post_json(EXPIRY_URL, payload)
    if err or not data:
        return None, err or "Empty expiry response"
    try:
        code = (data.get("data") or [{}])[0].get("expiryCode")
        if not code:
            return None, "Expiry code missing"
        update_cache(expiry_cache, code)
        return code, None
    except Exception as e:
        return None, f"Expiry parse error: {type(e).__name__}: {e}"


def fetch_option_chain(latest_ltp=None):
    cached = cached_data(option_cache, OC_CACHE_TTL)
    if cached is not None:
        return cached, None
    expiry_code, err = fetch_expiry()
    if err:
        return None, err
    payload = {
        "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
        "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
        "ExpiryCode": expiry_code,
    }
    data, err = post_json(OPTION_CHAIN_URL, payload)
    if err or not data:
        return None, err or "Empty option chain response"
    try:
        rows_raw = data.get("data") or []
        rows = []
        for item in rows_raw:
            strike = item.get("strikePrice")
            ce = item.get("CE", {}) or {}
            pe = item.get("PE", {}) or {}
            ce_ltp = safe_price(ce)
            pe_ltp = safe_price(pe)
            rows.append(
                {
                    "Strike": strike if strike is not None else "-",
                    "CE LTP": ce_ltp if ce_ltp is not None else "-",
                    "PE LTP": pe_ltp if pe_ltp is not None else "-",
                    "CE OI": ce.get("openInterest", "-"),
                    "PE OI": pe.get("openInterest", "-"),
                    "CE Δ": estimate_delta(strike, latest_ltp, is_call=True),
                    "PE Δ": estimate_delta(strike, latest_ltp, is_call=False),
                }
            )
        update_cache(option_cache, rows)
        return rows, None
    except Exception as e:
        return None, f"Option chain parse error: {type(e).__name__}: {e}"


# ---------- INTELLIGENCE ----------
def estimate_delta(strike, spot, is_call=True):
    if strike is None or spot is None:
        return "-"
    try:
        strike = float(strike)
        m = (spot - strike) / spot
        base = max(min(m * 4 + 0.5, 0.99), 0.01)
        if not is_call:
            base = -(1 - base)
        return round(base, 2)
    except Exception:
        return "-"


def find_atm_strike(rows, spot):
    if spot is None or not rows:
        return None
    try:
        strikes = [float(r["Strike"]) for r in rows if r["Strike"] != "-"]
        if not strikes:
            return None
        return min(strikes, key=lambda x: abs(x - spot))
    except Exception:
        return None


def compute_pcr(rows):
    try:
        total_ce = sum(
            float(r["CE OI"]) for r in rows if r["CE OI"] not in ("-", None, "")
        )
        total_pe = sum(
            float(r["PE OI"]) for r in rows if r["PE OI"] not in ("-", None, "")
        )
        if total_ce == 0:
            return None
        return round(total_pe / total_ce, 2)
    except Exception:
        return None


def find_highest_oi_strike(rows, side="CE"):
    key = f"{side} OI"
    try:
        valid = [
            (r["Strike"], float(r[key]))
            for r in rows
            if r[key] not in ("-", None, "") and r["Strike"] != "-"
        ]
        if not valid:
            return None
        return max(valid, key=lambda x: x[1])[0]
    except Exception:
        return None


def smart_strike_selection(rows, spot, num=5):
    if not rows or spot is None:
        return rows
    try:
        strikes = sorted(
            [r for r in rows if r["Strike"] != "-"],
            key=lambda r: abs(float(r["Strike"]) - spot),
        )
        return strikes[:num]
    except Exception:
        return rows


def compute_signal(candles, price):
    if not candles or price is None:
        return "NEUTRAL", "secondary", 50
    try:
        df = pd.DataFrame(candles)
        closes = df["close"].astype(float)
        if len(closes) < 2:
            return "NEUTRAL", "secondary", 50

        ema21 = closes.ewm(span=21, adjust=False).mean().iloc[-1]
        vwap_val = (closes * pd.Series(1, index=closes.index)).cumsum().iloc[-1] / len(
            closes
        )

        momentum = 0
        if len(closes) >= 5:
            momentum = closes.iloc[-1] - closes.iloc[-5]

        score = 0
        if price > ema21:
            score += 40
        elif price < ema21:
            score -= 40

        if price > vwap_val:
            score += 30
        elif price < vwap_val:
            score -= 30

        if momentum > 0:
            score += 30
        elif momentum < 0:
            score -= 30

        confidence = min(abs(score), 100)

        if score >= 60:
            return "STRONG BUY", "success", confidence
        elif score >= 20:
            return "WEAK BUY", "info", confidence
        elif score <= -60:
            return "STRONG SELL", "danger", confidence
        elif score <= -20:
            return "WEAK SELL", "warning", confidence
        else:
            return "NEUTRAL", "secondary", confidence
    except Exception:
        return "NEUTRAL", "secondary", 50


def generate_trade_plan(rows, spot, signal):
    if not rows or spot is None:
        return None, None
    try:
        near = smart_strike_selection(rows, spot, num=3)
        if not near:
            return None, None

        atm = find_atm_strike(near, spot)
        if atm is None:
            return None, None

        atm_row = next(
            (r for r in near if str(r["Strike"]) == str(atm)),
            near[0],
        )

        ce_ltp = safe_number(atm_row.get("CE LTP"))
        pe_ltp = safe_number(atm_row.get("PE LTP"))

        call_plan = None
        put_plan = None

        if ce_ltp and ce_ltp > 0 and "BUY" in signal:
            sl = round(ce_ltp * 0.7, 1)
            t1 = round(ce_ltp * 1.3, 1)
            t2 = round(ce_ltp * 1.6, 1)
            call_plan = {
                "type": "CALL BUY",
                "strike": atm,
                "entry": ce_ltp,
                "sl": sl,
                "t1": t1,
                "t2": t2,
            }

        if pe_ltp and pe_ltp > 0 and "SELL" in signal:
            sl = round(pe_ltp * 0.7, 1)
            t1 = round(pe_ltp * 1.3, 1)
            t2 = round(pe_ltp * 1.6, 1)
            put_plan = {
                "type": "PUT BUY",
                "strike": atm,
                "entry": pe_ltp,
                "sl": sl,
                "t1": t1,
                "t2": t2,
            }

        return call_plan, put_plan
    except Exception:
        return None, None


# ---------- CANDLE BUILDER ----------
def update_candles(price, candles):
    candles = candles or []
    now = datetime.utcnow().replace(second=0, microsecond=0)
    bucket = now.isoformat()

    if not candles:
        candles.append(
            {
                "ts": bucket,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "ticks": 1,
            }
        )
        return candles[-MAX_CANDLES:]

    last = candles[-1]
    if last["ts"] == bucket:
        last["high"] = max(last["high"], price)
        last["low"] = min(last["low"], price)
        last["close"] = price
        last["ticks"] = last.get("ticks", 0) + 1
        candles[-1] = last
    else:
        candles.append(
            {
                "ts": bucket,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "ticks": 1,
            }
        )

    return candles[-MAX_CANDLES:]


# ---------- CHART BUILDERS ----------
def add_ema_traces(fig, x, series):
    try:
        s = pd.Series(list(series), index=pd.to_datetime(list(x)))
        for span, color in [(9, "#f1c40f"), (21, "#9b59b6"), (50, "#1abc9c")]:
            ema = s.ewm(span=span, adjust=False).mean()
            fig.add_trace(
                go.Scatter(
                    x=ema.index,
                    y=ema.values,
                    mode="lines",
                    line=dict(width=1.4, color=color),
                    name=f"EMA {span}",
                )
            )
    except Exception:
        pass


def add_vwap_trace(fig, x, series):
    try:
        s = pd.Series(list(series), index=pd.to_datetime(list(x)))
        weights = pd.Series(1, index=s.index)
        vwap = (s * weights).cumsum() / weights.cumsum()
        fig.add_trace(
            go.Scatter(
                x=vwap.index,
                y=vwap.values,
                mode="lines",
                line=dict(width=1.4, color="#e67e22", dash="dot"),
                name="VWAP",
            )
        )
    except Exception:
        pass


def add_prev_high_low(fig, candles):
    try:
        if len(candles) < 2:
            return
        prev = candles[-2]
        x_range = [
            pd.to_datetime(candles[0]["ts"]),
            pd.to_datetime(candles[-1]["ts"]),
        ]
        for level, color, label in [
            (prev["high"], "#2ecc71", "Prev H"),
            (prev["low"], "#e74c3c", "Prev L"),
        ]:
            fig.add_shape(
                type="line",
                x0=x_range[0],
                x1=x_range[1],
                y0=level,
                y1=level,
                line=dict(color=color, width=1, dash="dash"),
            )
            fig.add_annotation(
                x=x_range[1],
                y=level,
                text=label,
                showarrow=False,
                font=dict(color=color, size=11),
                xanchor="right",
            )
    except Exception:
        pass


def build_price_figure(candles, history, mode="candle", ltp=None):
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0b0e11",
        plot_bgcolor="#0b0e11",
        font={"size": 13, "color": "#e0e0e0"},
        margin=dict(l=30, r=10, t=40, b=30),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend=dict(orientation="h", y=1.02, x=0),
    )

    if mode == "line":
        if history:
            df = pd.DataFrame(history)
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["price"],
                    mode="lines",
                    line=dict(color="#2ecc71", width=2),
                    name="LTP",
                )
            )
            add_ema_traces(fig, df["time"], df["price"])
            add_vwap_trace(fig, df["time"], df["price"])
    else:
        if candles:
            df = pd.DataFrame(candles)
            fig.add_trace(
                go.Candlestick(
                    x=df["ts"],
                    open=df["open"],
                    high=df["high"],
                    low=df["low"],
                    close=df["close"],
                    increasing_line_color="#2ecc71",
                    increasing_fillcolor="#2ecc71",
                    decreasing_line_color="#e74c3c",
                    decreasing_fillcolor="#e74c3c",
                    name="Price",
                    showlegend=False,
                )
            )
            add_ema_traces(fig, df["ts"], df["close"])
            add_vwap_trace(fig, df["ts"], df["close"])
            add_prev_high_low(fig, candles)
            if "ticks" in df.columns:
                fig.add_trace(
                    go.Bar(
                        x=df["ts"],
                        y=df["ticks"],
                        name="Tick Vol",
                        marker_color="#34495e",
                        opacity=0.4,
                        yaxis="y2",
                    )
                )
                fig.update_layout(
                    yaxis2=dict(
                        overlaying="y",
                        side="right",
                        showgrid=False,
                        tickfont=dict(color="#95a5a6"),
                        title="Ticks",
                    )
                )

    if ltp is not None:
        try:
            fig.add_hline(
                y=ltp,
                line_dash="dot",
                line_color="#ffffff",
                annotation_text=f"LTP {ltp:.2f}",
                annotation_position="top right",
                annotation_font_color="#ffffff",
            )
        except Exception:
            pass

    return fig


# ---------- UI HELPERS ----------
def make_trade_card(plan, color):
    if plan is None:
        return dbc.Card(
            dbc.CardBody(html.P("No signal", className="text-muted mb-0")),
            color="dark",
            outline=True,
            className="h-100",
        )
    return dbc.Card(
        dbc.CardBody(
            [
                html.H6(plan["type"], className=f"text-{color} fw-bold"),
                html.P(f"Strike: {plan['strike']}", className="mb-1 small"),
                html.P(f"Entry: {plan['entry']}", className="mb-1 small"),
                html.P(f"SL: {plan['sl']}", className="mb-1 small text-danger"),
                html.P(
                    f"T1: {plan['t1']}  T2: {plan['t2']}",
                    className="mb-0 small text-success",
                ),
            ]
        ),
        color="dark",
        outline=True,
        className="h-100",
    )


def build_table_styles(atm, highest_ce_oi, highest_pe_oi):
    styles = []
    if atm is not None:
        styles.append(
            {
                "if": {"filter_query": f"{{Strike}} = {atm}"},
                "backgroundColor": "#1f3b4d",
                "fontWeight": "bold",
                "border": "2px solid #3498db",
            }
        )
        styles.append(
            {
                "if": {"filter_query": f"{{Strike}} < {atm}"},
                "backgroundColor": "#0f1e0f",
            }
        )
        styles.append(
            {
                "if": {"filter_query": f"{{Strike}} > {atm}"},
                "backgroundColor": "#1e0f0f",
            }
        )
    for strike in [highest_ce_oi, highest_pe_oi]:
        if strike is not None:
            styles.append(
                {
                    "if": {"filter_query": f"{{Strike}} = {strike}"},
                    "border": "2px solid #e67e22",
                }
            )
    styles.append({"if": {"state": "active"}, "backgroundColor": "#2c3e50"})
    return styles


# ---------- APP ----------
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

HEADER_STYLE = {
    "position": "sticky",
    "top": 0,
    "zIndex": 999,
    "backgroundColor": "#0b0e11",
    "padding": "8px 0",
    "borderBottom": "1px solid #1f2229",
}

app.layout = dbc.Container(
    [
        # Header
        dbc.Row(
            [
                dbc.Col(
                    html.H2("🔥 AI Trading Terminal", className="mb-0"),
                    xs=12,
                    md=5,
                ),
                dbc.Col(
                    dbc.Badge(
                        "NEUTRAL",
                        id="signal-badge",
                        color="secondary",
                        className="px-3 py-2 fs-6",
                    ),
                    xs=6,
                    md=3,
                    className="text-md-center mt-2 mt-md-0",
                ),
                dbc.Col(
                    dbc.Alert(
                        "Waiting...",
                        id="status",
                        color="secondary",
                        className="mb-0 text-center py-1",
                    ),
                    xs=6,
                    md=4,
                ),
            ],
            align="center",
            style=HEADER_STYLE,
            className="g-2",
        ),
        # LTP row
        dbc.Row(
            [
                dbc.Col(
                    html.H3(id="ltp", className="mb-1 fw-bold text-success"),
                    xs=6,
                    md=3,
                ),
                dbc.Col(
                    html.Div(id="timestamp", className="text-muted small mt-2"),
                    xs=6,
                    md=3,
                ),
                dbc.Col(
                    dcc.RadioItems(
                        id="chart-mode",
                        options=[
                            {"label": " Candles", "value": "candle"},
                            {"label": " Line", "value": "line"},
                        ],
                        value="candle",
                        inline=True,
                        inputClassName="me-1",
                        labelStyle={"marginRight": "14px"},
                        className="text-light mt-2",
                    ),
                    xs=12,
                    md=6,
                    className="text-md-end",
                ),
            ],
            className="g-2 mt-2",
        ),
        # Stats row
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.P("ATM", className="text-muted small mb-1"),
                                html.H5(id="stat-atm", className="mb-0"),
                            ]
                        ),
                        className="text-center",
                        color="dark",
                    ),
                    xs=6,
                    md=3,
                    className="mb-2",
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.P("PCR", className="text-muted small mb-1"),
                                html.H5(id="stat-pcr", className="mb-0"),
                            ]
                        ),
                        className="text-center",
                        color="dark",
                    ),
                    xs=6,
                    md=3,
                    className="mb-2",
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.P("Signal", className="text-muted small mb-1"),
                                html.H5(id="stat-signal", className="mb-0"),
                            ]
                        ),
                        className="text-center",
                        color="dark",
                    ),
                    xs=6,
                    md=3,
                    className="mb-2",
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.P(
                                    "Confidence", className="text-muted small mb-1"
                                ),
                                html.H5(id="stat-confidence", className="mb-0"),
                            ]
                        ),
                        className="text-center",
                        color="dark",
                    ),
                    xs=6,
                    md=3,
                    className="mb-2",
                ),
            ],
            className="g-2 mt-1",
        ),
        # Chart
        dbc.Row(
            dbc.Col(
                dcc.Graph(
                    id="price-chart",
                    style={"minHeight": "420px"},
                    config={"scrollZoom": True, "displaylogo": False},
                ),
                xs=12,
            ),
            className="gy-2",
        ),
        # Option chain
        dbc.Row(
            dbc.Col(
                dash_table.DataTable(
                    id="table",
                    columns=[
                        {"name": "Strike", "id": "Strike"},
                        {"name": "CE LTP", "id": "CE LTP"},
                        {"name": "PE LTP", "id": "PE LTP"},
                        {"name": "CE OI", "id": "CE OI"},
                        {"name": "PE OI", "id": "PE OI"},
                        {"name": "CE Δ", "id": "CE Δ"},
                        {"name": "PE Δ", "id": "PE Δ"},
                    ],
                    page_size=18,
                    style_table={"overflowX": "auto", "backgroundColor": "#0b0e11"},
                    style_cell={
                        "backgroundColor": "#111418",
                        "color": "#e0e0e0",
                        "padding": "6px",
                        "border": "1px solid #1f2229",
                        "fontSize": 13,
                    },
                    style_header={
                        "backgroundColor": "#0f1217",
                        "fontWeight": "bold",
                        "border": "1px solid #1f2229",
                    },
                    tooltip_header={
                        "CE Δ": "Estimated delta (rough, no IV)",
                        "PE Δ": "Estimated delta",
                        "CE OI": "Call Open Interest (support/resistance level)",
                        "PE OI": "Put Open Interest (support/resistance level)",
                    },
                    tooltip_delay=0,
                    tooltip_duration=None,
                    sort_action="native",
                ),
                xs=12,
            ),
            className="gy-3",
        ),
        # Trade cards
        dbc.Row(
            [
                dbc.Col(
                    html.Div(id="call-card"),
                    xs=12,
                    md=6,
                    className="mb-2",
                ),
                dbc.Col(
                    html.Div(id="put-card"),
                    xs=12,
                    md=6,
                    className="mb-2",
                ),
            ],
            className="gy-2",
        ),
        # Stores
        dcc.Store(id="history-store", data=[]),
        dcc.Store(id="ohlc-store", data=[]),
        dcc.Store(id="last-ltp", data=None),
        dcc.Interval(id="ltp-interval", interval=LTP_INTERVAL_MS, n_intervals=0),
        dcc.Interval(id="oc-interval", interval=OC_INTERVAL_MS, n_intervals=0),
    ],
    fluid=True,
    className="pt-2 pb-4",
    style={"backgroundColor": "#0b0e11"},
)


# ---------- CALLBACKS ----------
@app.callback(
    Output("ltp", "children"),
    Output("timestamp", "children"),
    Output("status", "children"),
    Output("status", "color"),
    Output("price-chart", "figure"),
    Output("history-store", "data"),
    Output("ltp-interval", "interval"),
    Output("ohlc-store", "data"),
    Output("last-ltp", "data"),
    Output("signal-badge", "children"),
    Output("signal-badge", "color"),
    Output("stat-signal", "children"),
    Output("stat-confidence", "children"),
    Input("ltp-interval", "n_intervals"),
    State("history-store", "data"),
    State("ltp-interval", "interval"),
    State("ohlc-store", "data"),
    State("chart-mode", "value"),
    prevent_initial_call=False,
)
def update_ltp(_n, history, current_interval, candles, chart_mode):
    history = history or []
    candles = candles or []

    ltp, err = fetch_ltp()
    if err or ltp is None:
        new_interval = exponential_backoff(current_interval, failed=True)
        status_text = err or "Unknown LTP error"
        fig = build_price_figure(candles, history, chart_mode)
        return (
            "ERROR",
            datetime.now().strftime("%H:%M:%S"),
            status_text,
            "warning",
            fig,
            history,
            new_interval,
            candles,
            history[-1]["price"] if history else None,
            "NEUTRAL",
            "secondary",
            "NEUTRAL",
            "0%",
        )

    timestamp = datetime.now().strftime("%H:%M:%S")
    history.append({"time": timestamp, "price": ltp})
    history = history[-MAX_POINTS:]
    candles = update_candles(ltp, candles)

    signal_text, signal_color, confidence = compute_signal(candles, ltp)
    fig = build_price_figure(candles, history, chart_mode, ltp)

    return (
        f"{ltp:.2f}",
        timestamp,
        "LIVE",
        "success",
        fig,
        history,
        LTP_INTERVAL_MS,
        candles,
        ltp,
        signal_text,
        signal_color,
        signal_text,
        f"{confidence}%",
    )


@app.callback(
    Output("table", "data"),
    Output("table", "style_data_conditional"),
    Output("status", "children", allow_duplicate=True),
    Output("status", "color", allow_duplicate=True),
    Output("oc-interval", "interval"),
    Output("stat-atm", "children"),
    Output("stat-pcr", "children"),
    Output("call-card", "children"),
    Output("put-card", "children"),
    Input("oc-interval", "n_intervals"),
    State("oc-interval", "interval"),
    State("last-ltp", "data"),
    State("signal-badge", "children"),
    prevent_initial_call=False,
)
def update_option_chain(_n, current_interval, latest_ltp, signal):
    rows, err = fetch_option_chain(latest_ltp)
    if err or rows is None:
        new_int = exponential_backoff(current_interval, failed=True)
        return (
            no_update,
            no_update,
            err or "OC error",
            "warning",
            new_int,
            "-",
            "-",
            make_trade_card(None, "secondary"),
            make_trade_card(None, "secondary"),
        )

    atm = find_atm_strike(rows, latest_ltp)
    pcr = compute_pcr(rows)
    highest_ce = find_highest_oi_strike(rows, "CE")
    highest_pe = find_highest_oi_strike(rows, "PE")
    style = build_table_styles(atm, highest_ce, highest_pe)
    call_plan, put_plan = generate_trade_plan(rows, latest_ltp, signal or "NEUTRAL")

    atm_display = str(int(atm)) if atm is not None else "-"
    pcr_display = str(pcr) if pcr is not None else "-"

    return (
        rows,
        style,
        "LIVE",
        "success",
        OC_INTERVAL_MS,
        atm_display,
        pcr_display,
        make_trade_card(call_plan, "success"),
        make_trade_card(put_plan, "danger"),
    )


# ---------- RUN ----------
if __name__ == "__main__":
    print(f"Running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
