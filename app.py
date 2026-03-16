import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from dhanhq import dhanhq

st.set_page_config(layout="wide")

st.title("📊 NIFTY Options Dashboard")

# -----------------------------
# ENV VARIABLES
# -----------------------------

CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

if not CLIENT_ID or not ACCESS_TOKEN:
    st.error("Dhan API credentials missing")
    st.stop()

# -----------------------------
# DHAN API INIT
# -----------------------------

dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)

# -----------------------------
# FETCH NIFTY SPOT
# -----------------------------

spot_price = None

try:

    spot = dhan.ohlc_data(
        securities={"IDX_I":[13]}
    )

    data = spot.get("data", {})

    for exch in data.values():
        for sec in exch.values():

            spot_price = (
                sec.get("last_price")
                or sec.get("lastPrice")
                or sec.get("close")
                or sec.get("ltp")
            )

except Exception as e:
    st.error("Spot price fetch failed")
    st.write(e)

# -----------------------------
# SAFE DISPLAY
# -----------------------------

if spot_price is None:

    st.warning("⚠️ Spot price not available from API")

else:

    st.metric("NIFTY Spot", round(float(spot_price),2))


# -----------------------------
# FETCH EXPIRY
# -----------------------------

expiry = None

try:

    expiry_data = dhan.expiry_list(
        under_security_id=13,
        under_exchange_segment="IDX_I"
    )

    expiry_list = expiry_data.get("data",{}).get("data",[])

    if len(expiry_list)>0:
        expiry = expiry_list[0]

except:
    pass

if expiry is None:
    st.error("Expiry not available")
    st.stop()

st.write("Nearest Expiry:", expiry)

# -----------------------------
# OPTION CHAIN
# -----------------------------

rows=[]

try:

    option_chain = dhan.option_chain(
        under_security_id=13,
        under_exchange_segment="IDX_I",
        expiry=expiry
    )

    oc = option_chain.get("data",{}).get("data",{}).get("oc",{})

    for strike,data in oc.items():

        ce=data.get("ce",{})
        pe=data.get("pe",{})

        rows.append({

            "Strike":float(strike),

            "CE_OI":ce.get("oi",0),
            "PE_OI":pe.get("oi",0),

            "CE_LTP":ce.get("last_price",0),
            "PE_LTP":pe.get("last_price",0)

        })

except Exception as e:

    st.error("Option chain fetch failed")
    st.write(e)
    st.stop()

df=pd.DataFrame(rows)

# -----------------------------
# PCR
# -----------------------------

total_ce=df["CE_OI"].sum()
total_pe=df["PE_OI"].sum()

pcr=0

if total_ce>0:
    pcr=total_pe/total_ce

st.metric("PCR",round(pcr,2))

# -----------------------------
# SUPPORT RESISTANCE
# -----------------------------

support=df.loc[df["PE_OI"].idxmax()]["Strike"]
resistance=df.loc[df["CE_OI"].idxmax()]["Strike"]

col1,col2=st.columns(2)

col1.metric("Support",support)
col2.metric("Resistance",resistance)

# -----------------------------
# OI CHART
# -----------------------------

fig=go.Figure()

fig.add_bar(
    x=df["Strike"],
    y=df["CE_OI"],
    name="Call OI"
)

fig.add_bar(
    x=df["Strike"],
    y=df["PE_OI"],
    name="Put OI"
)

fig.update_layout(
    title="Open Interest Distribution",
    xaxis_title="Strike",
    yaxis_title="OI"
)

st.plotly_chart(fig,use_container_width=True)

# -----------------------------
# TABLE
# -----------------------------

st.subheader("Option Chain")

st.dataframe(df)
