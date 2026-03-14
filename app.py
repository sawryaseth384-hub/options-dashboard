import streamlit as st
import google.generativeai as genai

st.set_page_config(layout="wide")

st.title("AI Options Trading Dashboard")

# ---- AI API KEY ----
genai.configure(api_key="YOUR_GOOGLE_API_KEY")

model = genai.GenerativeModel("gemini-1.5-flash")

# ---- Dashboard Layout ----
col1, col2 = st.columns([3,1])

with col1:
    st.subheader("Market Data")
    st.info("Market data section will appear here")

with col2:
    st.subheader("AI Trading Assistant")

    user_prompt = st.text_area("Ask AI about Market")

    if st.button("Analyze Market"):
        if user_prompt:
            response = model.generate_content(user_prompt)
            st.success(response.text)
