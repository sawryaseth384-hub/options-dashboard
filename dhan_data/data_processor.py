def process_quote(data):
    result = []

    if data.get("status") != "success":
        return result

    try:
        segments = data.get("data", {})

        for segment, securities in segments.items():

            for sec_id, values in securities.items():

                if not values:
                    continue

                ltp = values.get("last_price", 0)
                oi = values.get("oi", 0)
                volume = values.get("volume", 0)
                buy_qty = values.get("buy_quantity", 0)
                sell_qty = values.get("sell_quantity", 0)

                # 🔥 BUY/SELL PRESSURE
                if buy_qty > sell_qty:
                    sentiment = "🟢 Buy Pressure"
                elif sell_qty > buy_qty:
                    sentiment = "🔴 Sell Pressure"
                else:
                    sentiment = "⚖️ Neutral"

                result.append({
                    "security_id": sec_id,
                    "ltp": ltp,
                    "oi": oi,
                    "volume": volume,
                    "buy_qty": buy_qty,
                    "sell_qty": sell_qty,
                    "sentiment": sentiment
                })

    except Exception as e:
        print("❌ Processing Error:", e)

    return result
