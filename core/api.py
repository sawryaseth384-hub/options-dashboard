# core/api.py

def fetch_data():

    # 👉 अभी dummy (replace with your Dhan API)
    return {
        "NIFTY": {"ltp": 23700, "change": 120},
        "BANKNIFTY": {"ltp": 55200, "change": 300},
        "SENSEX": {"ltp": 78500, "change": 250},
        "VIX": {"ltp": 18.2, "change": -0.5},

        "DOW": {"ltp": 38000, "change": 200},
        "NASDAQ": {"ltp": 16500, "change": -50},
        "GIFT": {"ltp": 23750, "change": 80},

        "CRUDE": {"ltp": 6500, "change": 30},
        "GOLD": {"ltp": 72000, "change": 100},
        "SILVER": {"ltp": 85000, "change": 200},

        "USDINR": {"ltp": 83.1, "change": 0.1},
        "DXY": {"ltp": 104.2, "change": -0.2},

        "FII": 1200,
        "PCR": 1.2
    }
