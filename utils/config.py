import streamlit as st

def get_config():
    try:
        return {
            "ACCESS_TOKEN": st.secrets["ACCESS_TOKEN"],
            "CLIENT_ID": st.secrets["CLIENT_ID"]
        }
    except Exception as e:
        return {
            "ACCESS_TOKEN": "",
            "CLIENT_ID": "",
            "error": str(e)
        }

config = get_config()

ACCESS_TOKEN = config["ACCESS_TOKEN"]
CLIENT_ID = config["CLIENT_ID"]
