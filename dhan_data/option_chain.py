rows = []

for strike, options in oc.items():

    try:
        strike = float(strike)

        ce = options.get("ce", {})
        pe = options.get("pe", {})

        rows.append({
            "Strike": strike,

            # CALL
            "Call OI": ce.get("oi", 0),
            "Call LTP": ce.get("last_price", 0),
            "Call Delta": ce.get("greeks", {}).get("delta", 0),
            "Call Theta": ce.get("greeks", {}).get("theta", 0),
            "Call Gamma": ce.get("greeks", {}).get("gamma", 0),
            "Call Vega": ce.get("greeks", {}).get("vega", 0),
            "Call IV": ce.get("implied_volatility", 0),

            # PUT
            "Put OI": pe.get("oi", 0),
            "Put LTP": pe.get("last_price", 0),
            "Put Delta": pe.get("greeks", {}).get("delta", 0),
            "Put Theta": pe.get("greeks", {}).get("theta", 0),
            "Put Gamma": pe.get("greeks", {}).get("gamma", 0),
            "Put Vega": pe.get("greeks", {}).get("vega", 0),
            "Put IV": pe.get("implied_volatility", 0),
        })

    except:
        continue
