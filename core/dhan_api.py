from dhan_data.option_chain import get_expiry_list, get_option_chain as fetch_option_chain

NIFTY_SECURITY_ID = 13


def get_option_chain():
    expiries, err = get_expiry_list(NIFTY_SECURITY_ID, "NSE_INDEX")
    if err:
        return {"_error": err}
    if not expiries:
        return {"_error": "Expiry list empty"}
    data, err = fetch_option_chain(NIFTY_SECURITY_ID, expiry=expiries[0], segment="NSE_INDEX")
    if err:
        return {"_error": err}
    return data
