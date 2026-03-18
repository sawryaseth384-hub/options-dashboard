import requests
import streamlit as st


class MarketQuote:

    def __init__(self):
        self.url = "https://api.dhan.co/v2/marketfeed/quote"

    def get_data(self, instruments):

        ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]
        CLIENT_ID = st.secrets["CLIENT_ID"]

        headers = {
            "access-token": ACCESS_TOKEN,
            "client-id": CLIENT_ID,
            "Content-Type": "application/json"
        }

        try:
            res = requests.post(self.url, headers=headers, json=instruments)

            return {
                "status_code": res.status_code,
                "data": res.json()
            }

        except Exception as e:
            return {"error": str(e)}
