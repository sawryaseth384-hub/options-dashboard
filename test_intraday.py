from core.dhan_v2 import get_intraday

SECURITY_ID = "13"  # NIFTY
SEGMENT = "NSE_INDEX"

data = get_intraday(SECURITY_ID, SEGMENT)
print("Response:", data)
