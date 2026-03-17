def process_quote(data):
    result = []

    # 🔴 API error handle
    if data.get("status") != "success":
        print("API Error:", data)
        return result

    try:
        segments = data.get("data", {})

        for segment, instruments in segments.items():
            for sec_id, values in instruments.items():

                processed = {
                    "segment": segment,
                    "security_id": sec_id,

                    # 🔥 CORE DATA
                    "ltp": values.get("last_price", 0),
                    "oi": values.get("oi", 0),
                    "volume": values.get("volume", 0),

                    # 🔥 ORDER FLOW
                    "buy_qty": values.get("buy_quantity", 0),
                    "sell_qty": values.get("sell_quantity", 0),

                    # 🔥 OI RANGE
                    "oi_high": values.get("oi_day_high", 0),
                    "oi_low": values.get("oi_day_low", 0),

                    # 🔥 PRICE RANGE
                    "open": values.get("ohlc", {}).get("open", 0),
                    "high": values.get("ohlc", {}).get("high", 0),
                    "low": values.get("ohlc", {}).get("low", 0),
                    "close": values.get("ohlc", {}).get("close", 0),
                }

                result.append(processed)

    except Exception as e:
        print("Processing Error:", e)

    return result
