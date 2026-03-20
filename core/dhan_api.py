from datetime import datetime
import time

def get_valid_expiries():
    expiries = get_expiry_list()
    valid = []

    for exp in expiries:
        try:
            dt = datetime.strptime(exp, "%Y-%m-%d")

            # 👉 सिर्फ Tuesday (1 = Tuesday)
            if dt.weekday() == 1:
                valid.append(exp)

        except:
            continue

    return valid
