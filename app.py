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
        if symbol in section:
            return section[symbol]
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


@st.cache_data(show_spinner=False)
def load_market_data():
    try:
        return build_market_data()
    except Exception as exc:
        return {"_error": str(exc)}


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
        return pd.DataFrame(columns=["Symbol", "LTP", "Change %", "High", "Low"])
    if isinstance(stocks, dict):
        stocks = stocks.get("data") or stocks.get("stocks") or []
    df = pd.DataFrame(stocks)
    if df.empty:
        return pd.DataFrame(columns=["Symbol", "LTP", "Change %", "High", "Low"])
    rename_map = {
        "symbol": "Symbol",
        "name": "Symbol",
        "ticker": "Symbol",
        "ltp": "LTP",
        "last_price": "LTP",
        "price": "LTP",
        "change_pct": "Change %",
        "changePercent": "Change %",
        "change_percentage": "Change %",
        "change%": "Change %",
        "pct_change": "Change %",
        "high": "High",
        "low": "Low",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    for col in ["Symbol", "LTP", "Change %", "High", "Low"]:
        if col not in df.columns:
            df[col] = None
    return df[["Symbol", "LTP", "Change %", "High", "Low"]]


def normalize_option_chain(options_data):
    if options_data is None:
        return pd.DataFrame(columns=["Strike", "Call OI", "Put OI", "Call LTP", "Put LTP"])
    if isinstance(options_data, dict):
        chain = options_data.get("chain") or options_data.get("oc") or options_data.get("option_chain")
    else:
        chain = options_data
    if chain is None:
        return pd.DataFrame(columns=["Strike", "Call OI", "Put OI", "Call LTP", "Put LTP"])
    if isinstance(chain, list):
        df = pd.DataFrame(chain)
        rename_map = {
            "strike": "Strike",
            "call_oi": "Call OI",
            "put_oi": "Put OI",
            "call_ltp": "Call LTP",
            "put_ltp": "Put LTP",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        for col in ["Strike", "Call OI", "Put OI", "Call LTP", "Put LTP"]:
            if col not in df.columns:
                df[col] = None
        return df[["Strike", "Call OI", "Put OI", "Call LTP", "Put LTP"]]
    rows = []
    for strike, row in chain.items():
        call = row.get("CE") or row.get("ce") or {}
        put = row.get("PE") or row.get("pe") or {}
        rows.append({
            "Strike": _to_float(strike),
            "Call OI": call.get("oi"),
            "Put OI": put.get("oi"),
            "Call LTP": call.get("ltp") or call.get("last_price"),
            "Put LTP": put.get("ltp") or put.get("last_price"),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["Strike", "Call OI", "Put OI", "Call LTP", "Put LTP"])
    return df[["Strike", "Call OI", "Put OI", "Call LTP", "Put LTP"]]


def resolve_spot_price(options_data, market_data):
    spot = None
    if isinstance(options_data, dict):
        spot = options_data.get("spot") or options_data.get("underlying_ltp") or options_data.get("ltp")
    if spot is None:
        spot = _get_value(_get_section(market_data, ["indices", "indian_market", "market"]), ["NIFTY", "BANKNIFTY"])
    return _to_float(spot)


if not build_market_data:
    st.error(f"Data engine unavailable: {IMPORT_ERROR}")
    st.stop()

if st.button("🔄 Refresh Data"):
    load_market_data.clear()
    st.experimental_rerun()

market_data = load_market_data()
if not market_data:
    st.warning("No Data")
    st.stop()
if isinstance(market_data, dict) and market_data.get("_error"):
    st.error(f"Data refresh failed: {market_data['_error']}")
    st.stop()

indian_section = _get_section(market_data, ["indices", "indian_market", "market", "header", "headers"])
global_section = _get_section(market_data, ["global", "commodities", "global_commodities"])
currency_section = _get_section(market_data, ["currency", "currencies", "fx"])

render_header_row("Indian Market", ["NIFTY", "BANKNIFTY", "FINNIFTY", "VIX"], indian_section)
render_header_row("Global + Commodity", ["DOW", "NASDAQ", "GIFT", "CRUDE"], global_section)
render_header_row("Currency", ["USDINR", "DXY"], currency_section)

st.divider()
st.subheader("📋 Live Market Scanner")

stocks_df = normalize_stocks(market_data.get("stocks") if isinstance(market_data, dict) else None)
if stocks_df.empty:
    st.warning("No Data")
else:
    stocks_df["Change %"] = pd.to_numeric(stocks_df["Change %"], errors="coerce")
    stocks_df["LTP"] = pd.to_numeric(stocks_df["LTP"], errors="coerce")
    sort_by = st.selectbox("Sort By", ["Change %", "LTP", "Symbol"], index=0)
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
option_chain_df = normalize_option_chain(options_data)
if option_chain_df.empty:
    st.warning("No Data")
else:
    option_chain_df["Call OI"] = pd.to_numeric(option_chain_df["Call OI"], errors="coerce")
    option_chain_df["Put OI"] = pd.to_numeric(option_chain_df["Put OI"], errors="coerce")
    total_call = option_chain_df["Call OI"].sum()
    total_put = option_chain_df["Put OI"].sum()
    pcr = None
    if isinstance(options_data, dict):
        pcr = options_data.get("pcr") or options_data.get("PCR")
    if pcr is None and total_call and total_call != 0:
        pcr = total_put / total_call
    st.metric("PCR (Put/Call Ratio)", "No Data" if pcr is None else f"{pcr:.2f}")

    spot_price = resolve_spot_price(options_data, market_data)
    atm_strike = None
    if spot_price is not None and not option_chain_df["Strike"].isna().all():
        option_chain_df["Strike"] = pd.to_numeric(option_chain_df["Strike"], errors="coerce")
        strike_diff = (option_chain_df["Strike"] - spot_price).abs()
        atm_index = strike_diff.idxmin()
        atm_strike = option_chain_df.loc[atm_index, "Strike"]

    def highlight_atm(row):
        if atm_strike is None:
            return [""] * len(row)
        return ["background-color: #ffeeba" if row["Strike"] == atm_strike else "" for _ in row]

    st.dataframe(option_chain_df.style.apply(highlight_atm, axis=1), use_container_width=True)

st.divider()
st.subheader("📉 Intraday Chart")

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
    else:
        intraday_df["close"] = pd.to_numeric(intraday_df["close"], errors="coerce")
        intraday_df = intraday_df.dropna(subset=["close"])
        if intraday_df.empty:
            st.warning("No Data")
        else:
            intraday_df["EMA"] = intraday_df["close"].ewm(span=21).mean()
            st.line_chart(intraday_df[["close", "EMA"]])
