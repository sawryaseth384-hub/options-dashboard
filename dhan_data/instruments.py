import pandas as pd

def get_instrument_list():

    url = "https://images.dhan.co/api-data/api-scrip-master.csv"

    try:
        df = pd.read_csv(url)

        return df.head(10).to_dict(orient="records")

    except Exception as e:
        return {"error": str(e)}
