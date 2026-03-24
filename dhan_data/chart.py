def get_candle_data(security_id, segment):

    # 🔥 INDEX HANDLE (NIFTY / BANKNIFTY)
    if segment == "IDX_I":

        import requests
        import pandas as pd
        from datetime import datetime, timedelta
        from core.token_manager import get_headers

        BASE_URL = "https://api.dhan.co/v2"

        # 🔥 Map index IDs
        index_map = {
            13: "26000",     # NIFTY
            25: "26009",     # BANKNIFTY
            27: "26037"      # FINNIFTY (approx, verify if needed)
        }

        chart_id = index_map.get(security_id)

        if not chart_id:
            return None

        payload = {
            "securityId": chart_id,
            "exchangeSegment": "NSE_IDX",
            "instrument": "INDEX",
            "interval": "5",
            "oi": False,
            "fromDate": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "toDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        res = requests.post(
            f"{BASE_URL}/charts/intraday",
            headers=get_headers(),
            json=payload
        )

        data = res.json()

        if "data" not in data:
            return None

        d = data["data"]

        df = pd.DataFrame({
            "time": pd.to_datetime(d["timestamp"], unit="s"),
            "open": d["open"],
            "high": d["high"],
            "low": d["low"],
            "close": d["close"],
            "volume": d.get("volume", [0]*len(d["timestamp"]))
        })

        return df.sort_values("time")

    # 🔥 STOCK / FNO (OLD LOGIC CONTINUE)
    else:
        from dhan_data.historical_data import get_historical
        import pandas as pd

        hist = get_historical(security_id, segment)

        if hist:
            df = pd.DataFrame(hist)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            return df

        return None
