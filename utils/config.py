import streamlit as st

def get_config():
    try:
        return {
            "ACCESS_TOKEN": st.secrets["ACCESS_TOKEN"],import streamlit as st
from dhanhq import DhanContext, dhanhq

client_id = st.secrets["1106299230"]
access_token = st.secrets["eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzczODg1OTg5LCJpYXQiOjE3NzM3OTk1ODksInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2Mjk5MjMwIn0.vRYxbB0OWqCIQ02J741rAoGugbSg3DV2bU1Ub-un-mAs-8QMzTFKCbnIp0RiC3AGASX4zVfmFS1nHRRYaYPmkQ"]

dhan_context = DhanContext(client_id, access_token)
dhan = dhanhq(dhan_context)

st.write("✅ Connected to Dhan API")
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
