import requests

def get_instrument_list():

    url = "https://api.dhan.co/v2/instruments"

    response = requests.get(url)

    return response.json()
