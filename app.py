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
MAX_POINTS = 800
OC_CACHE_TTL = 15
EXPIRY_CACHE_TTL = 300
BACKOFF_CAP_MS = 30000
MOMENTUM_LOOKBACK = 8
MAX_CANDLES = 200

# ---------- CACHE ----------
option_cache = {"data": [], "time": 0}
expiry_cache = {"code": None, "time": 0}

# ---------- HELPERS ----------
def safe_price(value_dict: dict):
    if not value_dict:
        return None
    for key in ("ltp", "lastPrice", "LTP", "price"):
        val = value_dict.get(key)
        if val is not None:
            try:
                return float(val)
            except Exception:
                continue
    return None

def safe_number(val):
    try:
        return float(val)
    except Exception:
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

def fetch_ltp():
    payload = {"NSE_INDEX": [UNDERLYINGS["NIFTY"]["id"]]}
    data, err = post_json(LTP_URL, payload)
    if err or not data:
        return None, err or "Empty LTP response"
    try:
        arr = data.get("data") or []
        if not arr:
            return None, "LTP response missing data"
        price = safe_number(arr[0].get("lastPrice")) or safe_number(arr[0].get("ltp")) or safe_number(arr[0].get("price"))
        if price is None:
            return None, "LTP price missing"
        return price, None
    except Exception as e:
        return None, f"LTP parse error: {type(e).__name__}: {e}"

def fetch_expiry():
    cached = cached_data(expiry_cache, EXPIRY_CACHE_TTL)
    if cached:
        return cached, None
    payload = {"UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"], "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"]}
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
            ce = item.get("CE", {})
            pe = item.get("PE", {})
            ce_oi = ce.get("openInterest")
            pe_oi = pe.get("openInterest")
            rows.append(
                {
                    "Strike": strike if strike is not None else "-",
                    "CE LTP": safe_price(ce) if safe_price(ce) is not None else "-",
                    "PE LTP": safe_price(pe) if safe_price(pe) is not None else "-",
                    "CE OI": ce_oi if ce_oi is not None else "-",
                    "PE OI": pe_oi if pe_oi is not None else "-",
                    "CE Δ": estimate_delta(strike, latest_ltp, is_call=True),
                    "PE Δ": estimate_delta(strike, latest_ltp, is_call=False),
                }
            )
        update_cache(option_cache, rows)
        return rows, None
    except Exception as e:
        return None, f"Option chain parse error: {type(e).__name__}: {e}"

# ---------- SIGNALS ----------
def compute_signal(candles, price):
    if not candles or price is None:
        return ("NEUTRAL", "secondary", 50)
    df = pd.DataFrame(candles)
    closes = df["close"]
    ema21 = closes.ewm(span=21, adjust=False).mean()
    vwap = (closes * df["ticks"]).cumsum() / df["ticks"].cumsum()
    score = 50
    if not ema21.empty:
        ema_v = ema21.iloc[-1]
        score += 12 if price > ema_v else -12
    if not vwap.empty:
        vwap_v = vwap.iloc[-1]
        score += 10 if price > vwap_v else -10
    if len(closes) >= MOMENTUM_LOOKBACK:
        window = closes.iloc[-MOMENTUM_LOOKBACK:]
        mom = (window.iloc[-1] - window.iloc[0]) / window.iloc[0]
        score += max(min(mom * 200, 15), -15)
    score = max(min(int(score), 100), 0)
    if score >= 80:
        return ("STRONG BUY", "success", score)
    if score >= 60:
        return ("WEAK BUY", "success", score)
    if score <= 20:
        return ("STRONG SELL", "danger", score)
    if score <= 40:
        return ("WEAK SELL", "danger", score)
    return ("NEUTRAL", "secondary", score)

def compute_entry_signal(price, candles):
    if not candles or price is None:
        return "NEUTRAL"
    df = pd.DataFrame(candles)
    closes = df["close"]
    ema = closes.ewm(span=21, adjust=False).mean()
    vwap = (closes * df["ticks"]).cumsum() / df["ticks"].cumsum()
    if ema.empty or vwap.empty:
        return "NEUTRAL"
    ema_v, vwap_v = ema.iloc[-1], vwap.iloc[-1]
    mom = 0
    if len(closes) >= MOMENTUM_LOOKBACK:
        window = closes.iloc[-MOMENTUM_LOOKBACK:]
        mom = (window.iloc[-1] - window.iloc[0]) / window.iloc[0]
    if price > ema_v and price > vwap_v and mom >= 0:
        return "CALL BUY"
    if price < ema_v and price < vwap_v and mom <= 0:
        return "PUT BUY"
    return "NEUTRAL"

# ---------- PCR ----------
def compute_pcr(rows):
    try:
        ce_oi = [safe_number(r["CE OI"]) for r in rows if r["CE OI"] != "-"]
        pe_oi = [safe_number(r["PE OI"]) for r in rows if r["PE OI"] != "-"]
        ce_sum = sum([x for x in ce_oi if x is not None])
        pe_sum = sum([x for x in pe_oi if x is not None])
        if ce_sum == 0:
            return "-"
        return round(pe_sum / ce_sum, 2)
    except Exception:
        return "-"

# ---------- SMART STRIKE ----------
def select_best_strike(rows, spot, is_call=True):
    if spot is None or not rows:
        return None
    preferred_deltas = (0.3, 0.6) if is_call else (-0.6, -0.3)
    side_delta = "CE Δ" if is_call else "PE Δ"
    side_oi = "CE OI" if is_call else "PE OI"
    side_ltp = "CE LTP" if is_call else "PE LTP"
    candidates = []
    for r in rows:
        try:
            strike = float(r["Strike"])
        except Exception:
            continue
        d = safe_number(r.get(side_delta))
        oi = safe_number(r.get(side_oi))
        ltp = safe_number(r.get(side_ltp))
        if d is None or oi is None or ltp is None:
            continue
        delta_ok = preferred_deltas[0] <= d <= preferred_deltas[1]
        proximity = abs(strike - spot)
        score = 0
        if delta_ok:
            score += 50
        score += max(0, 20 - proximity / 10)
        score += min(30, (oi / 1_000_000) * 30)
        candidates.append((score, strike, ltp, oi, d, r))
    if not candidates:
        return None
    best = sorted(candidates, key=lambda x: (-x[0], abs(x[1] - spot), -x[3]))[0]
    return {"strike": best[1], "ltp": best[2], "oi": best[3], "delta": best[4], "row": best[5]}

# ---------- CHARTS ----------
def base_price_figure():
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0b0e11",
        plot_bgcolor="#0b0e11",
        font={"size": 14, "color": "#e0e0e0"},
        margin=dict(l=30, r=10, t=40, b=30),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )
    return fig

def add_ema_traces(fig, x, series):
    try:
        s = pd.Series(series, index=pd.to_datetime(x))
        for span, color in [(9, "#f1c40f"), (21, "#9b59b6"), (50, "#1abc9c")]:
            ema = s.ewm(span=span, adjust=False).mean()
            fig.add_trace(go.Scatter(x=ema.index, y=ema.values, mode="lines", line=dict(width=1.5, color=color), name=f"EMA {span}"))
    except Exception:
        pass

def add_vwap_trace(fig, x, series):
    try:
        s = pd.Series(series, index=pd.to_datetime(x))
        weights = pd.Series(1, index=s.index)
        vwap = (s * weights).cumsum() / weights.cumsum()
        fig.add_trace(go.Scatter(x=vwap.index, y=vwap.values, mode="lines", line=dict(width=1.4, color="#e67e22", dash="dot"), name="VWAP"))
    except Exception:
        pass

def add_reference_levels(fig, df, last_price):
    if last_price is not None:
        fig.add_hline(y=last_price, line=dict(color="#e67e22", dash="dash"), opacity=0.6, annotation_text="LTP")
    if len(df) >= 2:
        prev = df.iloc[-2]
        fig.add_hline(y=prev["high"], line=dict(color="#16a085", dash="dot"), opacity=0.4, annotation_text="Prev High")
        fig.add_hline(y=prev["low"], line=dict(color="#c0392b", dash="dot"), opacity=0.4, annotation_text="Prev Low")

def build_price_figure(candles, history, mode, last_price):
    fig = base_price_figure()
    if mode == "line":
        if history:
            df = pd.DataFrame(history)
            fig.add_trace(go.Scatter(x=df["time"], y=df["price"], mode="lines", line=dict(color="#2ecc71", width=2), name="LTP"))
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
            fig.add_trace(go.Bar(x=df["ts"], y=df["ticks"], name="Tick Vol", marker_color="#34495e", opacity=0.4, yaxis="y2"))
            fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, tickfont=dict(color="#95a5a6"), title="Ticks"))
            add_reference_levels(fig, df, last_price)
    return fig

# ---------- CANDLE BUILDER ----------
def update_candles(price, candles):
    candles = candles or []
    now = datetime.utcnow().replace(second=0, microsecond=0)
    bucket = now.isoformat()
    if not candles:
        candles.append({"ts": bucket, "open": price, "high": price, "low": price, "close": price, "ticks": 1})
        return candles[-MAX_CANDLES:]
    last = candles[-1]
    if last["ts"] == bucket:
        last["high"] = max(last["high"], price)
        last["low"] = min(last["low"], price)
        last["close"] = price
        last["ticks"] = last.get("ticks", 0) + 1
        candles[-1] = last
    else:
        candles.append({"ts": bucket, "open": price, "high": price, "low": price, "close": price, "ticks": 1})
    return candles[-MAX_CANDLES:]

# ---------- UI COMPONENTS ----------
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server  # required for gunicorn / Railway

HEADER_STYLE = {
    "position": "sticky",
    "top": 0,
    "zIndex": 999,
    "backgroundColor": "#0b0e11",
    "padding": "8px 0",
    "borderBottom": "1px solid #1f2229",
}

def mini_stat(label, value, color="light"):
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(label, className="text-muted small"),
                html.Div(value, className=f"h5 mb-0 text-{color}"),
            ]
        ),
        className="bg-dark border-0 px-2 py-1",
    )

def trade_card(title, body_lines):
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(title, className="text-muted small mb-1"),
                *[html.Div(line, className="text-light") for line in body_lines],
            ]
        ),
        className="bg-dark border-0 px-2 py-1",
    )

app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(html.H2("🔥 AI Trading Terminal", className="mb-0"), xs=12, md=6),
                dbc.Col(dbc.Badge("NEUTRAL", id="signal-badge", color="secondary", className="px-3 py-2 fs-5"), xs=6, md=3, className="text-md-center mt-2 mt-md-0"),
                dbc.Col(dbc.Alert("Waiting...", id="status", color="secondary", className="mb-0 text-center"), xs=6, md=3),
            ],
            align="center",
            style=HEADER_STYLE,
            className="g-2",
        ),
        dbc.Row(
            [
                dbc.Col(html.H3(id="ltp", className="mb-1"), xs=6, md=3),
                dbc.Col(html.Div(id="timestamp", className="text-muted"), xs=6, md=3),
                dbc.Col(
                    dcc.RadioItems(
                        id="chart-mode",
                        options=[{"label": "Candles", "value": "candle"}, {"label": "Line", "value": "line"}],
                        value="candle",
                        inline=True,
                        inputClassName="me-1",
                        labelStyle={"marginRight": "12px"},
                        className="text-light",
                    ),
                    xs=12,
                    md=6,
                    className="text-md-end",
                ),
            ],
            className="g-2 mt-2",
        ),
        dbc.Row(
            [
                dbc.Col(mini_stat("ATM", "-", "info"), xs=4, md=2, id="atm-card"),
                dbc.Col(mini_stat("PCR", "-", "warning"), xs=4, md=2, id="pcr-card"),
                dbc.Col(mini_stat("Trend", "-", "light"), xs=4, md=2, id="trend-card"),
                dbc.Col(mini_stat("Signal", "-", "light"), xs=4, md=2, id="sig-card"),
                dbc.Col(mini_stat("Confidence", "-", "light"), xs=4, md=2, id="conf-card"),
            ],
            className="g-2 mb-2",
        ),
        dbc.Row(
            dbc.Col(
                dcc.Graph(
                    id="price-chart",
                    style={"minHeight": "430px"},
                    config={"scrollZoom": True, "displaylogo": False},
                    figure=base_price_figure(),
                ),
                xs=12,
            ),
            className="gy-3",
        ),
        dbc.Row(
            [
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
                        tooltip_header={"CE Δ": "Estimated delta (rough, no IV)", "PE Δ": "Estimated delta"},
                        tooltip_delay=0,
                        tooltip_duration=None,
                        sort_action="native",
                    ),
                    xs=12,
                ),
            ],
            className="gy-3",
        ),
        dbc.Row(
            [
                dbc.Col(trade_card("CALL Plan", ["Strike: -", "Entry: -", "SL: -", "T1/T2: -/-"]), id="call-trade-card", xs=12, md=6),
                dbc.Col(trade_card("PUT Plan", ["Strike: -", "Entry: -", "SL: -", "T1/T2: -/-"]), id="put-trade-card", xs=12, md=6),
            ],
            className="gy-2",
        ),
        dcc.Store(id="history-store", data=[]),
        dcc.Store(id="ohlc-store", data=[]),
        dcc.Store(id="last-ltp", data=None),
        dcc.Store(id="strike-store", data={"call": None, "put": None}),
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
    Output("price-chart", "figure", allow_duplicate=True),
    Output("history-store", "data"),
    Output("ltp-interval", "interval"),
    Output("ohlc-store", "data"),
    Output("last-ltp", "data"),
    Output("signal-badge", "children"),
    Output("signal-badge", "color"),
    Output("pcr-card", "children"),
    Output("atm-card", "children"),
    Output("trend-card", "children"),
    Output("sig-card", "children"),
    Output("conf-card", "children"),
    Output("call-trade-card", "children"),
    Output("put-trade-card", "children"),
    Input("ltp-interval", "n_intervals"),
    State("history-store", "data"),
    State("ltp-interval", "interval"),
    State("ohlc-store", "data"),
    State("chart-mode", "value"),
    State("price-chart", "figure"),
    State("table", "data"),
    State("strike-store", "data"),
    prevent_initial_call=False,
)
def update_ltp(_n, history, current_interval, candles, chart_mode, _current_fig, table_rows, strike_store):
    history = history or []
    candles = candles or []
    table_rows = table_rows or []
    strike_store = strike_store or {"call": None, "put": None}

    ltp, err = fetch_ltp()
    if err or ltp is None:
        new_interval = exponential_backoff(current_interval, failed=True)
        status_text = err or "Unknown LTP error"
        fig = build_price_figure(candles, history, chart_mode, history[-1]["price"] if history else None)
        return (
            "ERROR",
            datetime.now().strftime("%H:%M:%S"),
            status_text,
            "warning",
            fig,
            history,
            new_interval,
            candles,
            (history[-1]["price"] if history else None),
            "NEUTRAL",
            "secondary",
            current_mini_stat("PCR", table_rows, default="-"),
            mini_stat("ATM", "-", "info").children,
            mini_stat("Trend", "-", "light").children,
            mini_stat("Signal", "-", "light").children,
            mini_stat("Confidence", "-", "light").children,
            trade_card("CALL Plan", ["Strike: -", "Entry: -", "SL: -", "T1/T2: -/-"]).children,
            trade_card("PUT Plan", ["Strike: -", "Entry: -", "SL: -", "T1/T2: -/-"]).children,
        )

    timestamp = datetime.now().strftime("%H:%M:%S")
    history.append({"time": timestamp, "price": ltp})
    history = history[-MAX_POINTS:]
    candles = update_candles(ltp, candles)

    signal_text, signal_color, score = compute_signal(candles, ltp)
    entry_bias = compute_entry_signal(ltp, candles)

    fig = build_price_figure(candles, history, chart_mode, ltp)

    pcr_val = compute_pcr(table_rows) if table_rows else "-"
    atm_val = find_atm_strike(table_rows, ltp)

    call_card, put_card = build_trade_cards(strike_store, candles, ltp)

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
        mini_stat("PCR", pcr_val, "warning").children,
        mini_stat("ATM", atm_val if atm_val else "-", "info").children,
        mini_stat("Trend", signal_text, "success" if "BUY" in signal_text else ("danger" if "SELL" in signal_text else "light")).children,
        mini_stat("Signal", entry_bias, "success" if "CALL" in entry_bias else ("danger" if "PUT" in entry_bias else "light")).children,
        mini_stat("Confidence", f"{score}", "light").children,
        call_card,
        put_card,
    )

@app.callback(
    Output("table", "data"),
    Output("table", "style_data_conditional"),
    Output("status", "children", allow_duplicate=True),
    Output("status", "color", allow_duplicate=True),
    Output("oc-interval", "interval"),
    Output("strike-store", "data"),
    Input("oc-interval", "n_intervals"),
    State("oc-interval", "interval"),
    State("last-ltp", "data"),
    prevent_initial_call=False,
)
def update_option_chain(_n, current_interval, latest_ltp):
    rows, err = fetch_option_chain(latest_ltp)
    if err or rows is None:
        new_int = exponential_backoff(current_interval, failed=True)
        return no_update, no_update, err or "OC error", "warning", new_int, no_update

    atm = find_atm_strike(rows, latest_ltp)
    style = build_table_styles(rows, atm)

    best_call = select_best_strike(rows, latest_ltp, is_call=True)
    best_put = select_best_strike(rows, latest_ltp, is_call=False)
    strike_store = {"call": best_call, "put": best_put}

    return rows, style, "LIVE", "success", OC_INTERVAL_MS, strike_store

# ---------- TABLE STYLES ----------
def find_atm_strike(rows, spot):
    if spot is None:
        return None
    try:
        strikes = [float(r["Strike"]) for r in rows if r["Strike"] != "-"]
        if not strikes:
            return None
        return min(strikes, key=lambda x: abs(x - spot))
    except Exception:
        return None

def build_table_styles(rows, atm):
    styles = []
    if atm is not None:
        styles.append({"if": {"filter_query": f"{{Strike}} = {atm}"}, "backgroundColor": "#1f3b4d", "fontWeight": "bold"})
        styles.append({"if": {"filter_query": f"{{Strike}} < {atm}"}, "backgroundColor": "#0f1e0f"})
        styles.append({"if": {"filter_query": f"{{Strike}} > {atm}"}, "backgroundColor": "#1e0f0f"})
    ce_max = max([safe_number(r["CE OI"]) for r in rows if r["CE OI"] != "-" and safe_number(r["CE OI"]) is not None] or [None], default=None)
    pe_max = max([safe_number(r["PE OI"]) for r in rows if r["PE OI"] != "-" and safe_number(r["PE OI"]) is not None] or [None], default=None)
    if ce_max:
        styles.append({"if": {"filter_query": f"{{CE OI}} = {ce_max}"}, "backgroundColor": "#264653"})
    if pe_max:
        styles.append({"if": {"filter_query": f"{{PE OI}} = {pe_max}"}, "backgroundColor": "#512c2c"})
    styles.append({"if": {"state": "active"}, "backgroundColor": "#2c3e50"})
    return styles

# ---------- TRADE PLAN ----------
def build_trade_cards(strike_store, candles, spot):
    last_low, last_high = None, None
    if candles:
        last_low = candles[-1]["low"]
        last_high = candles[-1]["high"]
    call_plan = trade_plan(strike_store.get("call"), spot, last_low, is_call=True)
    put_plan = trade_plan(strike_store.get("put"), spot, last_high, is_call=False)
    call_card = trade_card("CALL Plan", call_plan).children
    put_card = trade_card("PUT Plan", put_plan).children
    return call_card, put_card

def trade_plan(sel, spot, sl_level, is_call=True):
    if not sel or spot is None or sl_level is None:
        return ["Strike: -", "Entry: -", "SL: -", "T1/T2: -/-"]
    entry = sel["ltp"]
    if entry is None:
        return ["Strike: -", "Entry: -", "SL: -", "T1/T2: -/-"]
    risk_underlying = abs(spot - sl_level)
    if risk_underlying == 0:
        return ["Strike: -", "Entry: -", "SL: -", "T1/T2: -/-"]
    rr = 2
    delta = sel["delta"] if isinstance(sel["delta"], (int, float)) else 0.5
    option_risk = max(0.1, risk_underlying * abs(delta))
    sl_price = max(0.1, entry - option_risk)
    t1 = entry + option_risk * rr
    t2 = entry + option_risk * rr * 1.5
    return [f"Strike: {sel['strike']}", f"Entry: {entry:.2f}", f"SL: {sl_price:.2f}", f"T1/T2: {t1:.2f} / {t2:.2f}"]

# ---------- MINI STAT ----------
def current_mini_stat(label, rows, default="-"):
    if label == "PCR":
        pcr_val = compute_pcr(rows) if rows else default
        return mini_stat("PCR", pcr_val, "warning").children
    return mini_stat(label, default, "light").children

# ---------- RUN ----------
if __name__ == "__main__":
    print(f"Running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
