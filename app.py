import os
import time
import json
from datetime import datetime
import requests
import pandas as pd
import plotly.graph_objs as go
from dash import Dash, html, dcc, dash_table, Input, Output, State
import dash_bootstrap_components as dbc

# ---------- ENV ----------
CLIENT_ID = os.getenv("CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
PORT = int(os.environ.get("PORT", 8050))

# ---------- API ----------
LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
EXPIRY_URL = "https://api.dhan.co/v2/optionChain/expiryList"
OPTION_CHAIN_URL = "https://api.dhan.co/v2/optionChain"
UNDERLYINGS = {"NIFTY": {"id": 13, "segment": "IDX_I"}}

# ---------- SETTINGS ----------
LTP_INTERVAL_MS = 1000
OC_INTERVAL_MS = 8000
REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", 5))
MAX_POINTS = 150
OC_CACHE_TTL = 15
EXPIRY_CACHE_TTL = 300
BACKOFF_BASE_MS = 1000
BACKOFF_CAP_MS = 30000
MOMENTUM_PERIOD = 5
SL_MULTIPLIER = 0.80
TARGET_MULTIPLIER = 1.40
VOLUME_RANGE_MULTIPLIER = 10

# ---------- SESSION ----------
_session = requests.Session()
_session.headers.update({
    "access-token": DHAN_ACCESS_TOKEN or "",
    "client-id": CLIENT_ID or "",
    "Content-Type": "application/json",
})

# ---------- CACHE ----------
option_cache = {"data": [], "time": 0}
expiry_cache = {"code": None, "time": 0}
FALLBACK_ROWS = [{"Strike": "-", "CE LTP": "-", "PE LTP": "-", "CE OI": "-", "PE OI": "-"} for _ in range(10)]

# ---------- HELPERS ----------
def _post(url, payload, retries=3):
    delay = BACKOFF_BASE_MS / 1000.0
    for attempt in range(retries):
        try:
            r = _session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r, None
        except requests.exceptions.RequestException as exc:
            if attempt < retries - 1:
                time.sleep(min(delay, BACKOFF_CAP_MS / 1000.0))
                delay *= 2
            else:
                return None, f"{type(exc).__name__}: {exc}"


def fetch_ltp():
    payload = {"NSE_INDEX": [UNDERLYINGS["NIFTY"]["id"]]}
    r, err = _post(LTP_URL, payload)
    if err:
        return None, f"LTP error: {err}"
    data = r.json().get("data", {})
    price = None
    if isinstance(data, list) and data:
        price = data[0].get("ltp") or data[0].get("lastPrice")
    elif isinstance(data, dict):
        first_seg = next(iter(data.values()), {})
        if isinstance(first_seg, list) and first_seg:
            price = first_seg[0].get("ltp") or first_seg[0].get("lastPrice")
        elif isinstance(first_seg, dict):
            price = first_seg.get("ltp") or first_seg.get("lastPrice")
    if price is None:
        return None, "LTP error: empty data"
    return float(price), None


def fetch_expiry():
    now = time.time()
    if expiry_cache["code"] and now - expiry_cache["time"] < EXPIRY_CACHE_TTL:
        return expiry_cache["code"], None
    payload = {
        "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
        "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
    }
    r, err = _post(EXPIRY_URL, payload)
    if err:
        return None, f"Expiry error: {err}"
    data = r.json().get("data") or []
    if not data:
        return None, "Expiry error: empty data"
    first = data[0]
    code = first.get("expiryCode") if isinstance(first, dict) else first
    expiry_cache["code"] = code
    expiry_cache["time"] = now
    return code, None


def _extract_price(side):
    if not side:
        return None
    return side.get("ltp") or side.get("lastPrice") or side.get("LTP") or side.get("price")


def _extract_oi(side):
    if not side:
        return 0
    return int(side.get("openInterest") or side.get("oi") or side.get("OI") or 0)


def fetch_option_chain():
    now = time.time()
    if option_cache["data"] and now - option_cache["time"] < OC_CACHE_TTL:
        return option_cache["data"], None

    expiry_code, err = fetch_expiry()
    if err:
        return FALLBACK_ROWS, err

    payload = {
        "UnderlyingScrip": UNDERLYINGS["NIFTY"]["id"],
        "UnderlyingSeg": UNDERLYINGS["NIFTY"]["segment"],
        "ExpiryCode": expiry_code,
    }
    r, err = _post(OPTION_CHAIN_URL, payload)
    if err:
        return FALLBACK_ROWS, f"OC error: {err}"

    data = r.json().get("data")
    if not data:
        return FALLBACK_ROWS, "OC warning: empty data"

    rows = []
    for item in data:
        rows.append({
            "Strike": item.get("strikePrice"),
            "CE LTP": _extract_price(item.get("CE", {})),
            "PE LTP": _extract_price(item.get("PE", {})),
            "CE OI": _extract_oi(item.get("CE", {})),
            "PE OI": _extract_oi(item.get("PE", {})),
        })

    option_cache["data"] = rows
    option_cache["time"] = now
    return rows, None


# ---------- INDICATORS ----------
def compute_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def compute_vwap(df):
    if "volume" not in df.columns or df["volume"].sum() == 0:
        return pd.Series([None] * len(df), index=df.index)
    typical = df["price"]
    cumvol = df["volume"].cumsum()
    cumtpv = (typical * df["volume"]).cumsum()
    return cumtpv / cumvol


def compute_signals(df):
    if len(df) < 50:
        return "WAIT", "Not enough data"
    ema9 = compute_ema(df["price"], 9).iloc[-1]
    ema21 = compute_ema(df["price"], 21).iloc[-1]
    ema50 = compute_ema(df["price"], 50).iloc[-1]
    vwap = compute_vwap(df).iloc[-1]
    price = df["price"].iloc[-1]
    momentum = price - df["price"].iloc[-MOMENTUM_PERIOD] if len(df) >= MOMENTUM_PERIOD else 0

    if ema9 > ema21 > ema50 and price > vwap and momentum > 0:
        return "BUY", f"EMA9>{ema9:.0f} EMA21>{ema21:.0f} EMA50>{ema50:.0f} VWAP>{vwap:.0f} Mom+{momentum:.1f}"
    elif ema9 < ema21 < ema50 and price < vwap and momentum < 0:
        return "SELL", f"EMA9<{ema9:.0f} EMA21<{ema21:.0f} EMA50<{ema50:.0f} VWAP<{vwap:.0f} Mom{momentum:.1f}"
    return "NEUTRAL", f"EMA9={ema9:.0f} EMA21={ema21:.0f} VWAP={vwap:.0f}"


def compute_pcr(rows):
    try:
        total_ce = sum(r["CE OI"] for r in rows if isinstance(r.get("CE OI"), (int, float)))
        total_pe = sum(r["PE OI"] for r in rows if isinstance(r.get("PE OI"), (int, float)))
        if total_ce == 0:
            return None
        return round(total_pe / total_ce, 2)
    except Exception:
        return None


def select_strike(rows, ltp):
    if not ltp or not rows:
        return None, None, None
    best = None
    best_diff = float("inf")
    for r in rows:
        strike = r.get("Strike")
        if strike and isinstance(strike, (int, float)):
            diff = abs(float(strike) - ltp)
            if diff < best_diff:
                best_diff = diff
                best = r
    if not best:
        return None, None, None
    return best.get("Strike"), best.get("CE LTP"), best.get("PE LTP")


def _calc_sl_target(entry):
    sl = round(entry * SL_MULTIPLIER, 2)
    target = round(entry * TARGET_MULTIPLIER, 2)
    return sl, target


def generate_trade_plan(signal, ltp, strike, ce_ltp, pe_ltp):
    if signal == "BUY" and ce_ltp:
        try:
            entry = float(ce_ltp)
            sl, target = _calc_sl_target(entry)
            return f"📈 BUY CE @ {strike} | Entry: {entry} | SL: {sl} | Target: {target}"
        except Exception:
            pass
    elif signal == "SELL" and pe_ltp:
        try:
            entry = float(pe_ltp)
            sl, target = _calc_sl_target(entry)
            return f"📉 BUY PE @ {strike} | Entry: {entry} | SL: {sl} | Target: {target}"
        except Exception:
            pass
    return "⏸️ No trade plan — waiting for signal"


# ---------- CHART ----------
def build_chart(history):
    layout = go.Layout(
        template="plotly_dark",
        title="Live LTP + EMA + VWAP",
        xaxis_title="Time",
        yaxis_title="Price",
        legend=dict(orientation="h", y=1.02),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    if not history:
        return go.Figure(layout=layout)

    df = pd.DataFrame(history)
    traces = []

    # Candlestick-style: use OHLC if available, else line
    if "open" in df.columns:
        traces.append(go.Candlestick(
            x=df["time"], open=df["open"], high=df["high"],
            low=df["low"], close=df["price"], name="Price",
        ))
    else:
        traces.append(go.Scatter(
            x=df["time"], y=df["price"],
            mode="lines", name="LTP",
            line=dict(color="#17becf", width=2),
        ))
        # Tick volume as bar at bottom (secondary y)
        if "volume" in df.columns:
            traces.append(go.Bar(
                x=df["time"], y=df["volume"],
                name="Volume", marker_color="#636efa",
                opacity=0.3, yaxis="y2",
            ))

    if len(df) >= 9:
        ema9 = compute_ema(df["price"], 9)
        traces.append(go.Scatter(x=df["time"], y=ema9, mode="lines",
                                 name="EMA9", line=dict(color="#ff7f0e", width=1, dash="dot")))
    if len(df) >= 21:
        ema21 = compute_ema(df["price"], 21)
        traces.append(go.Scatter(x=df["time"], y=ema21, mode="lines",
                                 name="EMA21", line=dict(color="#2ca02c", width=1, dash="dash")))
    if len(df) >= 50:
        ema50 = compute_ema(df["price"], 50)
        traces.append(go.Scatter(x=df["time"], y=ema50, mode="lines",
                                 name="EMA50", line=dict(color="#d62728", width=1, dash="longdash")))

    vwap = compute_vwap(df)
    if vwap.notna().any():
        traces.append(go.Scatter(x=df["time"], y=vwap, mode="lines",
                                 name="VWAP", line=dict(color="#9467bd", width=1.5, dash="dashdot")))

    # Previous high/low reference lines
    if len(df) > 1:
        prev_high = df["price"].max()
        prev_low = df["price"].min()
        traces.append(go.Scatter(
            x=[df["time"].iloc[0], df["time"].iloc[-1]],
            y=[prev_high, prev_high],
            mode="lines", name="Prev High",
            line=dict(color="#1f77b4", width=1, dash="dot"), opacity=0.6,
        ))
        traces.append(go.Scatter(
            x=[df["time"].iloc[0], df["time"].iloc[-1]],
            y=[prev_low, prev_low],
            mode="lines", name="Prev Low",
            line=dict(color="#e377c2", width=1, dash="dot"), opacity=0.6,
        ))

    if "volume" in df.columns:
        layout.update(
            yaxis2=dict(overlaying="y", side="right", showgrid=False,
                        title="Volume", range=[0, df["volume"].max() * VOLUME_RANGE_MULTIPLIER])
        )

    return go.Figure(data=traces, layout=layout)


def next_interval(prev_ms, failed):
    if not failed:
        return LTP_INTERVAL_MS
    return min(prev_ms * 2, BACKOFF_CAP_MS)


# ---------- APP ----------
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    title="AI Trading Dashboard",
)
server = app.server

app.layout = dbc.Container(
    [
        html.H2("🔥 AI Trading Dashboard", className="mt-3 mb-2"),
        dbc.Row([
            dbc.Col(dbc.Alert("Initializing...", id="status", color="secondary"), width=12),
        ]),
        dbc.Row([
            dbc.Col(html.H3(id="ltp-display", children="LTP: --"), width=4),
            dbc.Col(html.Div(id="signal-display", children="Signal: --"), width=4),
            dbc.Col(html.Div(id="pcr-display", children="PCR: --"), width=2),
        ], className="mb-2"),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody(html.Div(id="trade-plan", children="Trade Plan: --")),
                             color="dark", outline=True), width=12),
        ], className="mb-3"),
        dcc.Loading(
            id="chart-loading",
            type="default",
            children=dcc.Graph(id="chart", style={"height": "420px"}),
        ),
        html.H5("Option Chain", className="mt-3"),
        dcc.Loading(
            id="table-loading",
            type="default",
            children=dash_table.DataTable(
                id="table",
                columns=[
                    {"name": "Strike", "id": "Strike"},
                    {"name": "CE LTP", "id": "CE LTP"},
                    {"name": "PE LTP", "id": "PE LTP"},
                    {"name": "CE OI", "id": "CE OI"},
                    {"name": "PE OI", "id": "PE OI"},
                ],
                page_size=20,
                style_cell={"backgroundColor": "#222", "color": "white", "textAlign": "center"},
                style_header={"backgroundColor": "#333", "fontWeight": "bold"},
            ),
        ),
        dcc.Store(id="history-store", data=[]),
        dcc.Interval(id="ltp-interval", interval=LTP_INTERVAL_MS, n_intervals=0),
        dcc.Interval(id="oc-interval", interval=OC_INTERVAL_MS, n_intervals=0),
    ],
    fluid=True,
)


# ---------- CALLBACKS ----------
@app.callback(
    Output("ltp-display", "children"),
    Output("status", "children"),
    Output("status", "color"),
    Output("chart", "figure"),
    Output("history-store", "data"),
    Output("ltp-interval", "interval"),
    Output("signal-display", "children"),
    Input("ltp-interval", "n_intervals"),
    State("history-store", "data"),
    State("ltp-interval", "interval"),
    prevent_initial_call=False,
)
def update_ltp(_n, history, current_interval):
    history = history or []
    ltp, err = fetch_ltp()

    if err:
        new_interval = next_interval(current_interval, failed=True)
        return (
            "LTP: ERROR", err, "warning",
            build_chart(history), history, new_interval, "Signal: --",
        )

    timestamp = datetime.now().strftime("%H:%M:%S")
    history.append({"time": timestamp, "price": ltp, "volume": 1})
    history = history[-MAX_POINTS:]

    df = pd.DataFrame(history)
    signal, reason = compute_signals(df)
    signal_color = {"BUY": "🟢", "SELL": "🔴"}.get(signal, "🟡")

    return (
        f"LTP: {ltp:.2f}",
        "● LIVE",
        "success",
        build_chart(history),
        history,
        LTP_INTERVAL_MS,
        f"{signal_color} Signal: {signal} — {reason}",
    )


@app.callback(
    Output("table", "data"),
    Output("status", "children", allow_duplicate=True),
    Output("status", "color", allow_duplicate=True),
    Output("oc-interval", "interval"),
    Output("pcr-display", "children"),
    Output("trade-plan", "children"),
    Input("oc-interval", "n_intervals"),
    State("oc-interval", "interval"),
    State("history-store", "data"),
    prevent_initial_call=False,
)
def update_option_chain(_n, current_interval, history):
    rows, err = fetch_option_chain()

    ltp = None
    if history:
        try:
            ltp = history[-1]["price"]
        except Exception:
            pass

    pcr = compute_pcr(rows)
    pcr_text = f"PCR: {pcr}" if pcr is not None else "PCR: N/A"

    strike, ce_ltp, pe_ltp = select_strike(rows, ltp)
    signal = "NEUTRAL"
    if history and len(history) >= 50:
        df = pd.DataFrame(history)
        signal, _ = compute_signals(df)
    trade_plan = generate_trade_plan(signal, ltp, strike, ce_ltp, pe_ltp)

    if err:
        new_int = next_interval(current_interval, failed=True)
        return rows, err, "warning", new_int, pcr_text, trade_plan

    return rows, "● LIVE", "success", OC_INTERVAL_MS, pcr_text, trade_plan


# ---------- RUN ----------
if __name__ == "__main__":
    print(f"Starting on port {PORT}")
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
    )
