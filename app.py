# -----------------------------
# FETCH NIFTY SPOT
# -----------------------------

spot_price = None

try:

    spot = dhan.ohlc_data(
        securities={"IDX_I":[13]}
    )

    data = spot.get("data")

    # Ensure data is dictionary
    if isinstance(data, dict):

        for exch in data.values():

            if isinstance(exch, dict):

                for sec in exch.values():

                    if isinstance(sec, dict):

                        spot_price = (
                            sec.get("last_price")
                            or sec.get("lastPrice")
                            or sec.get("close")
                            or sec.get("ltp")
                        )

except Exception as e:

    st.error("Spot price fetch failed")
    st.write(e)

# SAFE DISPLAY

if spot_price:

    st.metric("NIFTY Spot", round(float(spot_price),2))

else:

    st.warning("⚠️ Spot price not available from API")
