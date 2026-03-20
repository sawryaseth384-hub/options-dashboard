import streamlit as st   # 🔥 MUST ADD (top of file)


def get_candle_data(security_id, segment):

    try:
        import pandas as pd
        from datetime import datetime, timedelta
        import requests

        url = f"{BASE_URL}/charts/intraday"

        mapped_segment = map_segment(segment)
        instrument = get_instrument_type(segment)

        to_date = datetime.now()
        from_date = to_date - timedelta(days=1)

        payload = {
            "securityId": str(security_id),
            "exchangeSegment": mapped_segment,
            "instrument": instrument,
            "interval": "5",
            "oi": False,
            "fromDate": from_date.strftime("%Y-%m-%d %H:%M:%S"),
            "toDate": to_date.strftime("%Y-%m-%d %H:%M:%S")
        }

        res = requests.post(url, headers=get_headers(), json=payload)
        data = res.json()

        st.write("CHART RAW:", data)

        # ❌ safety check
        if not data or "open" not in data:
            return None

        # 🔥 FLATTEN FUNCTION
        def flatten(arr):
            flat = []
            for i in arr:
                if isinstance(i, list):
                    flat.extend(i)
                else:
                    flat.append(i)
            return flat

        open_ = flatten(data.get("open", []))
        high_ = flatten(data.get("high", []))
        low_ = flatten(data.get("low", []))
        close_ = flatten(data.get("close", []))
        volume_ = flatten(data.get("volume", []))
        time_ = flatten(data.get("timestamp", []))

        # ❌ empty data check
        if len(time_) == 0:
            return None

        df = pd.DataFrame({
            "open": open_,
            "high": high_,
            "low": low_,
            "close": close_,
            "volume": volume_,
            "time": pd.to_datetime(time_, unit="s")
        })

        return df

    except Exception as e:
        st.error(f"Chart Error: {e}")
        return None
