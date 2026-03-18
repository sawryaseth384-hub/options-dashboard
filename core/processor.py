def process_data(data):

    rows = []

    if data.get("status") != "success":
        return rows

    for segment, items in data["data"].items():
        for sec_id, values in items.items():

            rows.append({
                "Symbol": f"{segment}-{sec_id}",
                "LTP": values.get("last_price"),
                "Change": values.get("net_change", 0),
                "OI": values.get("oi"),
                "Volume": values.get("volume")
            })

    return rows
