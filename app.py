import streamlit as st
from utils.config import ACCESS_TOKEN, CLIENT_ID

st.write("TOKEN LENGTH:", len(ACCESS_TOKEN))
st.write("CLIENT ID:", CLIENT_ID)
from utils.config import config
import streamlit as st

st.write("CONFIG:", config)
