from dhan_data.option_chain import get_expiry_list, get_option_chain as fetch_option_chain


def get_option_chain():
    expiries, err = get_expiry_list(13, "NSE_INDEX")
    if err:
        return {"_error": err}
    if not expiries:
        return {"_error": "No expiry found"}
    data, err = fetch_option_chain(13, expiry=expiries[0], segment="NSE_INDEX")
    if err:
        return {"_error": err}
    return data
