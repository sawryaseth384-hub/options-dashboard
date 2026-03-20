import requests

def get_annexure():

    url = "https://api.dhan.co/v2/annexure"

    response = requests.get(url)

    return response.json()
