from dhanhq import dhanhq
import os

# environment variables
client_id = os.getenv("DHAN_CLIENT_ID")
access_token = os.getenv("DHAN_ACCESS_TOKEN")

# connect to Dhan
dhan = dhanhq(client_id, access_token)

# NIFTY security id = 13
data = dhan.marketfeed({
    "NSE_EQ": [13]
})

print(data)
