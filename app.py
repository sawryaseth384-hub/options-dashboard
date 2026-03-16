import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from dhanhq import dhanhq

st.set_page_config(layout="wide")

st.title("📊 NIFTY Options Dashboard")

# -----------------------
# Load Environment Keys
# -----------------------

CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN")

# Debug check
if CLIENT_ID is None or ACCESS_TOKEN is None:
    st.error("Dhan API credentials missing")

    st.write("Debug Info 👇")
    st.write("CLIENT_ID:", CLIENT_ID)
    st.write("ACCESS_TOKEN:", ACCESS_TOKEN)

    st.stop()

# -----------------------
# Initialize API
# -----------------------

dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)

# -----------------------
# Get NIFTY Spot
# -----------------------

try:

    spot = dhan.quote_data(
        securities={"IDX_I":[13]}
    )

    spot_data = spot.get("data",{})

    spot_price = list(spot_data.values())[0]["lastPrice"]

    st.metric("NIFTY Spot", spot_price)

except Exception as e:

    st.error("Spot price fetch failed")
    st.write(e)
    st.stop()

# -----------------------
# Get Expiry
# -----------------------

try:

    expiry_data = dhan.expiry_list(
        under_security_id=13,
        under_exchange_segment="IDX_I"
    )

    expiry = expiry_data["data"]["data"][0]

    st.write("Nearest Expiry:", expiry)

except Exception as e:

    st.error("Expiry fetch failed")
    st.write(e)
    st.stop()

# -----------------------
# Option Chain
# -----------------------

try:

    option_chain = dhan.option_chain(
        under_security_id=13,
        under_exchange_segment="IDX_I",
        expiry=expiry
    )

    oc = option_chain["data"]["data"]["oc"]

    rows = []

    for strike, data in oc.items():

        ce = data.get("ce",{})
        pe = data.get("pe",{})

        rows.append({

            "Strike": float(strike),

            "CE_OI": ce.get("oi",0),
            "CE_LTP": ce.get("last_price",0),

            "PE_OI": pe.get("oi",0),
            "PE_LTP": pe.get("last_price",0)

        })

    df = pd.DataFrame(rows)

except Exception as e:

    st.error("Option chain fetch failed")
    st.write(e)
    st.stop()

# -----------------------
# PCR
# -----------------------

total_ce = df["CE_OI"].sum()
total_pe = df["PE_OI"].sum()

pcr = total_pe / total_ce if total_ce != 0 else 0

st.metric("PCR", round(pcr,2))

# -----------------------
# Support / Resistance
# -----------------------

support = df.loc[df["PE_OI"].idxmax()]["Strike"]
resistance = df.loc[df["CE_OI"].idxmax()]["Strike"]

col1, col2 = st.columns(2)

col1.metric("Support", support)
col2.metric("Resistance", resistance)

# -----------------------
# OI Chart
# -----------------------

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
    title="Open Interest Distribution",
    xaxis_title="Strike",
    yaxis_title="OI"
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------
# Table
# -----------------------

st.subheader("Option Chain")

st.dataframe(df)
