import random

def fetch_data():
    # 🔥 fallback safe data (no crash)
    return {
        "nifty": {"ltp": 23700, "change": 120},
        "banknifty": {"ltp": 55200, "change": 300},
        "sensex": {"ltp": 78500, "change": 250},
        "vix": {"ltp": 18.2, "change": -0.5},

        "dow": {"ltp": 38000, "change": 200},
        "nasdaq": {"ltp": 16500, "change": -50},
        "gift": {"ltp": 23750, "change": 80},

        "crude": {"ltp": 6500, "change": 30},
        "gold": {"ltp": 72000, "change": 100},
        "silver": {"ltp": 85000, "change": 200},

        "usd": {"ltp": 83.1, "change": 0.1},
        "dxy": {"ltp": 104.2, "change": -0.2},
    }
