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

dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)

# -----------------------------
# EXPIRY
# -----------------------------

expiry_data = dhan.expiry_list(
    under_security_id=13,
    under_exchange_segment="IDX_I"
)

expiry = expiry_data["data"]["data"][0]

st.write("Nearest Expiry:", expiry)

# -----------------------------
# OPTION CHAIN
# -----------------------------

option_chain = dhan.option_chain(
    under_security_id=13,
    under_exchange_segment="IDX_I",
    expiry=expiry
)

oc = option_chain["data"]["data"]["oc"]

rows = []

for strike,data in oc.items():

    ce=data.get("ce",{})
    pe=data.get("pe",{})

    ce_oi=ce.get("oi",0)
    pe_oi=pe.get("oi",0)

    # Skip empty strikes
    if ce_oi==0 and pe_oi==0:
        continue

    rows.append({

        "Strike":float(strike),
        "CE_OI":ce_oi,
        "PE_OI":pe_oi,
        "CE_LTP":ce.get("last_price",0),
        "PE_LTP":pe.get("last_price",0)

    })

df=pd.DataFrame(rows)

# -----------------------------
# ATM / SPOT
# -----------------------------

atm_strike=df.iloc[(df["CE_OI"]+df["PE_OI"]).idxmax()]["Strike"]

st.metric("Approx NIFTY Spot",atm_strike)

# -----------------------------
# PCR
# -----------------------------

total_ce=df["CE_OI"].sum()
total_pe=df["PE_OI"].sum()

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
# OPTION CHAIN
# -----------------------------

st.subheader("Option Chain")

st.dataframe(df)
