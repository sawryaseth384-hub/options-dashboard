import streamlit as st
import pandas as pd

try:
    from dhan_data.market_data_engine import build_market_data
except Exception as exc:
    build_market_data = None
    IMPORT_ERROR = str(exc)

st.set_page_config(page_title="Trading Dashboard", layout="wide")
st.title("📈 Trading Dashboard")


def _get_section(data, keys):
    if not isinstance(data, dict):
        return None
    for key in keys:
        if key in data:
            return data[key]
    return None


def _find_symbol(section, symbol):
    symbol = symbol.upper()
    if section is None:
        return None
    if isinstance(section, dict):
        for key, value in section.items():
            if str(key).upper() == symbol:
                return value
    if isinstance(section, list):
        for item in section:
            name = str(item.get("symbol") or item.get("name") or item.get("ticker") or item.get("Symbol") or "").upper()
            if name == symbol:
                return item
    return None


def _get_value(item, keys):
    if not isinstance(item, dict):
        return None
    for key in keys:
        if key in item:
            return item[key]
    return None


def _to_float(value):
    try:
        return float(value)
    except Exception:
        return None


@st.cache_data(ttl=60, show_spinner=False)
def load_market_data():
    try:
        return build_market_data()
    except Exception as exc:
        return {"_meta": {"errors": [str(exc)]}}


def render_header_row(title, symbols, section):
    st.markdown(f"### {title}")
    cols = st.columns(len(symbols))
    for col, symbol in zip(cols, symbols):
        item = _find_symbol(section, symbol)
        ltp = _get_value(item, ["ltp", "LTP", "last_price", "price", "last"])
        change = _get_value(item, ["change_pct", "changePercent", "change_percentage", "change%", "pct_change", "Change %"])
        ltp_value = "No Data" if ltp is None else f"{_to_float(ltp):,.2f}"
        change_value = None if change is None else f"{_to_float(change):+.2f}%"
        col.metric(symbol, ltp_value, change_value)


def normalize_stocks(stocks):
    if stocks is None:
        return pd.DataFrame(columns=["Symbol", "LTP", "Volume", "Change %", "High", "Low"])
    if isinstance(stocks, dict):
        stocks = stocks.get("data") or stocks.get("stocks") or []
    df = pd.DataFrame(stocks)
    if df.empty:
        return pd.DataFrame(columns=["Symbol", "LTP", "Volume", "Change %", "High", "Low"])
    rename_map = {
        "symbol": "Symbol",
        "name": "Symbol",
        "ticker": "Symbol",
        "ltp": "LTP",
        "last_price": "LTP",
        "price": "LTP",
        "volume": "Volume",
        "change_pct": "Change %",
        "changePercent": "Change %",
        "change_percentage": "Change %",
        "change%": "Change %",
        "pct_change": "Change %",
        "high": "High",
        "low": "Low",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    for col in ["Symbol", "LTP", "Volume", "Change %", "High", "Low"]:
        if col not in df.columns:
            df[col] = None
    return df[["Symbol", "LTP", "Volume", "Change %", "High", "Low"]]


def normalize_option_chain(options_data):
    if options_data is None:
        return pd.DataFrame(columns=[
            "Strike", "Call LTP", "Call OI", "Call Volume", "Call IV",
            "Put LTP", "Put OI", "Put Volume", "Put IV"
        ])
    if isinstance(options_data, dict):
        chain = options_data.get("chain") or options_data.get("oc") or options_data.get("option_chain")
    else:
        chain = options_data
    if chain is None:
        return pd.DataFrame(columns=[
            "Strike", "Call LTP", "Call OI", "Call Volume", "Call IV",
            "Put LTP", "Put OI", "Put Volume", "Put IV"
        ])
    if isinstance(chain, list):
        df = pd.DataFrame(chain)
        if "ce" in df.columns or "pe" in df.columns:
            rows = []
            for row in chain:
                ce = row.get("ce") or {}
                pe = row.get("pe") or {}
                rows.append({
                    "Strike": row.get("strike"),
                    "Call LTP": ce.get("ltp"),
                    "Call OI": ce.get("oi"),
                    "Call Volume": ce.get("volume"),
                    "Call IV": ce.get("iv"),
                    "Put LTP": pe.get("ltp"),
                    "Put OI": pe.get("oi"),
                    "Put Volume": pe.get("volume"),
                    "Put IV": pe.get("iv")
                })
            df = pd.DataFrame(rows)
        else:
            rename_map = {
                "strike": "Strike",
                "call_oi": "Call OI",
                "put_oi": "Put OI",
                "call_ltp": "Call LTP",
                "put_ltp": "Put LTP",
            }
            df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        for col in [
            "Strike", "Call LTP", "Call OI", "Call Volume", "Call IV",
            "Put LTP", "Put OI", "Put Volume", "Put IV"
        ]:
            if col not in df.columns:
                df[col] = None
        return df[[
            "Strike", "Call LTP", "Call OI", "Call Volume", "Call IV",
            "Put LTP", "Put OI", "Put Volume", "Put IV"
        ]]
    rows = []
    for strike, row in chain.items():
        call = row.get("CE") or row.get("ce") or {}
        put = row.get("PE") or row.get("pe") or {}
        rows.append({
            "Strike": _to_float(strike),
            "Call LTP": call.get("ltp") or call.get("last_price"),
            "Call OI": call.get("oi"),
            "Call Volume": call.get("volume"),
            "Call IV": call.get("iv"),
            "Put LTP": put.get("ltp") or put.get("last_price"),
            "Put OI": put.get("oi"),
            "Put Volume": put.get("volume"),
            "Put IV": put.get("iv")
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=[
            "Strike", "Call LTP", "Call OI", "Call Volume", "Call IV",
            "Put LTP", "Put OI", "Put Volume", "Put IV"
        ])
    return df[[
        "Strike", "Call LTP", "Call OI", "Call Volume", "Call IV",
        "Put LTP", "Put OI", "Put Volume", "Put IV"
    ]]


def resolve_spot_price(options_data, market_data):
    spot = None
    if isinstance(options_data, dict):
        spot = options_data.get("spot") or options_data.get("underlying_ltp") or options_data.get("ltp")
    if spot is None:
        spot = _get_value(_find_symbol(_get_section(market_data, ["indian", "indices", "indian_market", "market"]), "NIFTY"), ["ltp", "LTP"])
    return _to_float(spot)


if not build_market_data:
    st.error(f"Data engine unavailable: {IMPORT_ERROR}")
    market_data = {
        "indian": {},
        "stocks": [],
        "options": {"chain": [], "pcr": 0},
        "_meta": {"errors": [IMPORT_ERROR]}
    }
else:
    if st.button("🔄 Refresh Data"):
        load_market_data.clear()
        st.experimental_rerun()

    market_data = load_market_data()

if not market_data:
    st.warning("No Data")
    market_data = {"indian": {}, "stocks": [], "options": {"chain": [], "pcr": 0}, "_meta": {"errors": []}}

if isinstance(market_data, dict):
    errors = market_data.get("_meta", {}).get("errors") or []
    if errors:
        with st.expander("API Errors"):
            for error in errors:
                st.write(error)

indian_section = _get_section(market_data, ["indian", "indices", "indian_market", "market", "header", "headers"])

render_header_row("Indian Market", ["NIFTY", "BANKNIFTY", "FINNIFTY", "VIX"], indian_section)

st.divider()
st.subheader("📋 Live Market Scanner")

stocks_df = normalize_stocks(market_data.get("stocks") if isinstance(market_data, dict) else None)
if stocks_df.empty:
    st.warning("No Data")
else:
    stocks_df["Change %"] = pd.to_numeric(stocks_df["Change %"], errors="coerce")
    stocks_df["LTP"] = pd.to_numeric(stocks_df["LTP"], errors="coerce")
    stocks_df["Volume"] = pd.to_numeric(stocks_df["Volume"], errors="coerce")
    sort_by = st.selectbox("Sort By", ["Change %", "LTP", "Volume", "Symbol"], index=0)
    sorted_df = stocks_df.sort_values(sort_by, ascending=False, na_position="last")
    st.dataframe(sorted_df, use_container_width=True)

    col1, col2 = st.columns(2)
    top_gainers = stocks_df.nlargest(5, "Change %", keep="all")
    top_losers = stocks_df.nsmallest(5, "Change %", keep="all")
    with col1:
        st.markdown("#### Top Gainers")
        st.dataframe(top_gainers, use_container_width=True)
    with col2:
        st.markdown("#### Top Losers")
        st.dataframe(top_losers, use_container_width=True)

st.divider()
st.subheader("📊 Options Analytics")

options_data = market_data.get("options") if isinstance(market_data, dict) else None
options_by_symbol = options_data.get("by_symbol") if isinstance(options_data, dict) else {}
available_symbols = list(options_by_symbol.keys()) if options_by_symbol else []
default_symbol = options_data.get("selected_symbol") if isinstance(options_data, dict) else None
symbol_index = available_symbols.index(default_symbol) if default_symbol in available_symbols else 0
selected_symbol = st.selectbox("Underlying", available_symbols or ["NIFTY"], index=symbol_index)
symbol_data = options_by_symbol.get(selected_symbol, {}) if options_by_symbol else {}
expiry_list = symbol_data.get("expiries") or []
default_expiry = options_data.get("selected_expiry") if isinstance(options_data, dict) else None
expiry_index = expiry_list.index(default_expiry) if default_expiry in expiry_list else 0
selected_expiry = st.selectbox("Expiry", expiry_list or ["No Data"], index=expiry_index)
chain_data = symbol_data.get("chains", {}).get(selected_expiry, {}) if symbol_data else {}
options_view = {
    "chain": chain_data.get("chain_filtered") or chain_data.get("chain"),
    "pcr": chain_data.get("pcr"),
    "atm": chain_data.get("atm"),
    "oi_analysis": chain_data.get("oi_analysis"),
    "spot": chain_data.get("spot")
}
option_chain_df = normalize_option_chain(options_view)
if option_chain_df.empty:
    st.warning("No Data")
else:
    option_chain_df["Call OI"] = pd.to_numeric(option_chain_df["Call OI"], errors="coerce")
    option_chain_df["Put OI"] = pd.to_numeric(option_chain_df["Put OI"], errors="coerce")
    total_call = option_chain_df["Call OI"].sum()
    total_put = option_chain_df["Put OI"].sum()
    pcr = options_view.get("pcr")
    if pcr is None and total_call and total_call != 0:
        pcr = total_put / total_call
    st.metric("PCR (Put/Call Ratio)", "No Data" if pcr is None else f"{pcr:.2f}")

    spot_price = resolve_spot_price(options_view, market_data)
    atm_strike = options_view.get("atm")
    if atm_strike is None and spot_price is not None and not option_chain_df["Strike"].isna().all():
        option_chain_df["Strike"] = pd.to_numeric(option_chain_df["Strike"], errors="coerce")
        strike_diff = (option_chain_df["Strike"] - spot_price).abs()
        atm_index = strike_diff.idxmin()
        atm_strike = option_chain_df.loc[atm_index, "Strike"]

    def highlight_atm(row):
        if atm_strike is None:
            return [""] * len(row)
        return ["background-color: #ffeeba" if row["Strike"] == atm_strike else "" for _ in row]

    st.dataframe(option_chain_df.style.apply(highlight_atm, axis=1), use_container_width=True)

    oi_data = options_view.get("oi_analysis") or {}
    summary = oi_data.get("summary") if isinstance(oi_data, dict) else None
    if isinstance(summary, dict):
        st.markdown("#### OI Analysis")
        summary_df = pd.DataFrame(
            [{"Signal": key, "Count": value} for key, value in summary.items()]
        )
        st.dataframe(summary_df, use_container_width=True)

st.divider()
st.subheader("📉 Intraday Chart")

intraday_df = None
intraday_data = _get_section(market_data, ["intraday", "chart", "intraday_data"])
if intraday_data is None:
    st.warning("No Data")
else:
    if isinstance(intraday_data, pd.DataFrame):
        intraday_df = intraday_data.copy()
    else:
        intraday_df = pd.DataFrame(intraday_data)
    if intraday_df.empty or "close" not in intraday_df.columns:
        st.warning("No Data")
        intraday_df = None
    else:
        intraday_df["close"] = pd.to_numeric(intraday_df["close"], errors="coerce")
        intraday_df = intraday_df.dropna(subset=["close"])
        if intraday_df.empty:
            st.warning("No Data")
            intraday_df = None

if intraday_df is not None and not intraday_df.empty:
    intraday_df["EMA"] = intraday_df["close"].ewm(span=21).mean()
    st.line_chart(intraday_df[["close", "EMA"]])
else:
    intraday_df = None

volume_spike = {}
if isinstance(market_data, dict):
    volume_spike = market_data.get("volume_spike") or {}
if volume_spike:
    spike = volume_spike.get("spike")
    if spike:
        st.warning("Volume spike detected")
    elif spike is False:
        st.info("No volume spike detected")

st.divider()
st.subheader("🧪 Debug Panel")
meta = market_data.get("_meta") if isinstance(market_data, dict) else {}
with st.expander("API Status & Errors", expanded=False):
    errors = meta.get("errors") if isinstance(meta, dict) else None
    if errors:
        st.error("API issues detected:")
        for err in errors:
            st.write(f"- {err}")
    else:
        st.success("API status: OK")
