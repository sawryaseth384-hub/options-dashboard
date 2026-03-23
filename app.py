import requests

url = "https://api.dhan.co/v2/optionchain/optionchain"

payload = {
    "UnderlyingScrip": 13,
    "UnderlyingSeg": "IDX_I",
    "Expiry": expiry
}

res = requests.post(url, headers=get_headers(), json=payload)

data = res.json()

st.write("Option Chain Raw Response")
st.json(data)
