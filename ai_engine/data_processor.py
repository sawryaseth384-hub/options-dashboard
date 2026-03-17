def process_quote(data):
    result = []

    if data.get("status") != "success":
        return result

    try:
        for segment in data.get("data", {}):
            for sec_id, values in data["data"][segment].items():

                if not values:
                    continue

                result.append({
                    "security_id": sec_id,
                    "ltp": values.get("last_price"),
                    "oi": values.get("oi"),
                    "volume": values.get("volume"),
                    "buy_qty": values.get("buy_quantity"),
                    "sell_qty": values.get("sell_quantity"),
                })

    except Exception as e:
        print("Processing Error:", e)

    return result
