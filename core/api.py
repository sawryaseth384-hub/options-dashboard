import random

# base data (initial)
base_data = [
    {"name": "NIFTY", "price": 23700},
    {"name": "BANKNIFTY", "price": 55200},
    {"name": "SENSEX", "price": 78500},
    {"name": "VIX", "price": 18.2},
    {"name": "DOW", "price": 38000},
    {"name": "NASDAQ", "price": 16500},
    {"name": "GIFT", "price": 23750},
    {"name": "CRUDE", "price": 6500},
    {"name": "GOLD", "price": 72000},
    {"name": "SILVER", "price": 85000},
    {"name": "USDINR", "price": 83.1},
    {"name": "DXY", "price": 104.2},
]

def fetch_data():
    data = []

    for item in base_data:
        change = round(random.uniform(-100, 100), 2)

        data.append({
            "name": item["name"],
            "price": round(item["price"] + change, 2),
            "change": change
        })

    return data
