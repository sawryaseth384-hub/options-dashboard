import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from dhanhq import dhanhq

st.set_page_config(layout="wide")

st.title("📊 NIFTY Options Dashboard")

# -------------------------
# ENV VARIABLES
# -------------------------

CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

if not CLIENT_ID or not ACCESS_TOKEN:
    st.error("Dhan API credentials missing")
    st.write("CLIENT_ID:", CLIENT_ID)
    st.write("ACCESS_TOKEN:", ACCESS_TOKEN)
    st.stop()

# -------------------------
# DHAN INIT
# -------------------------

dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)

# -------------------------
# NIFTY SPOT PRICE
# -------------------------

try:

    spot = dhan.ohlc_data(
        securities={"IDX_I":[13]}
    )

    spot_data = spot.get("data",{})

    if len(spot_data)==0:
        st.error("No spot data returned")
        st.stop()

    first = list(spot_data.values())[0]

    # Safe fallback
    spot_price = (
        first.get("last_price") or
        first.get("lastPrice") or
        first.get("close") or
        first.get("ltp")
    )

    st.metric("NIFTY Spot", round(float(spot_price),2))

except Exception as e:

    st.error("Spot price fetch failed")
    st.write(e)
    st.stop()

# -------------------------
# EXPIRY
# -------------------------

try:

    expiry_data = dhan.expiry_list(
        under_security_id=13,
        under_exchange_segment="IDX_I"
    )

    expiry = expiry_data.get("data",{}).get("data",[None])[0]

    if expiry is None:
        st.error("Expiry not found")
        st.stop()

    st.write("Nearest Expiry:", expiry)

except Exception as e:

    st.error("Expiry fetch failed")
    st.write(e)
    st.stop()

# -------------------------
# OPTION CHAIN
# -------------------------

try:

    option_chain = dhan.option_chain(
        under_security_id=13,
        under_exchange_segment="IDX_I",
        expiry=expiry
    )

    oc = option_chain.get("data",{}).get("data",{}).get("oc",{})

    rows=[]

    for strike,data in oc.items():

        ce=data.get("ce",{})
        pe=data.get("pe",{})

        rows.append({

            "Strike":float(strike),

            "CE_OI":ce.get("oi",0),
            "CE_LTP":ce.get("last_price",0),

            "PE_OI":pe.get("oi",0),
            "PE_LTP":pe.get("last_price",0)

        })

    df=pd.DataFrame(rows)

except Exception as e:

    st.error("Option chain fetch failed")
    st.write(e)
    st.stop()

# -------------------------
# PCR
# -------------------------

total_ce=df["CE_OI"].sum()
total_pe=df["PE_OI"].sum()

pcr=0

if total_ce>0:
    pcr=total_pe/total_ce

st.metric("PCR",round(pcr,2))

# -------------------------
# SUPPORT RESISTANCE
# -------------------------

support=df.loc[df["PE_OI"].idxmax()]["Strike"]
resistance=df.loc[df["CE_OI"].idxmax()]["Strike"]

col1,col2=st.columns(2)

col1.metric("Support",support)
col2.metric("Resistance",resistance)

# -------------------------
# OI CHART
# -------------------------

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

# -------------------------
# OPTION CHAIN TABLE
# -------------------------

st.subheader("Option Chain")

st.dataframe(df)
