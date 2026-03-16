import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from dhanhq import dhanhq

# -------------------------
# Dhan API Credentials
# -------------------------

CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)

st.set_page_config(layout="wide")

st.title("📊 NIFTY Options Dashboard")

# -------------------------
# NIFTY Spot Price
# -------------------------

spot = dhan.quote_data(
    securities={"IDX_I":[13]}
)

spot_price = spot["data"][0]["lastPrice"]

st.metric("NIFTY Spot", spot_price)

# -------------------------
# Expiry List
# -------------------------

expiry_data = dhan.expiry_list(
    under_security_id=13,
    under_exchange_segment="IDX_I"
)

expiry = expiry_data["data"]["data"][0]

st.write("Nearest Expiry:", expiry)

# -------------------------
# Option Chain
# -------------------------

option_chain = dhan.option_chain(
    under_security_id=13,
    under_exchange_segment="IDX_I",
    expiry=expiry
)

oc = option_chain["data"]["data"]["oc"]

rows = []

for strike, data in oc.items():

    ce = data.get("ce", {})
    pe = data.get("pe", {})

    rows.append({

        "Strike": float(strike),

        "CE_OI": ce.get("oi", 0),
        "CE_LTP": ce.get("last_price", 0),

        "PE_OI": pe.get("oi", 0),
        "PE_LTP": pe.get("last_price", 0)

    })

df = pd.DataFrame(rows)

# -------------------------
# PCR
# -------------------------

total_ce = df["CE_OI"].sum()
total_pe = df["PE_OI"].sum()

pcr = total_pe / total_ce if total_ce != 0 else 0

st.metric("PCR", round(pcr,2))

# -------------------------
# Support / Resistance
# -------------------------

support = df.loc[df["PE_OI"].idxmax()]["Strike"]
resistance = df.loc[df["CE_OI"].idxmax()]["Strike"]

col1, col2 = st.columns(2)

col1.metric("Support", support)
col2.metric("Resistance", resistance)

# -------------------------
# OI Chart
# -------------------------

fig = go.Figure()

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
    title="Open Interest",
    xaxis_title="Strike Price",
    yaxis_title="OI"
)

st.plotly_chart(fig, use_container_width=True)

# -------------------------
# Data Table
# -------------------------

st.subheader("Option Chain")

st.dataframe(df)
