from dhan_data.option_chain import get_option_chain as fetch_option_chain


def get_option_chain():
    data, err = fetch_option_chain(13, expiry="2026-03-24", segment="NSE_INDEX")
    if err:
        return {"_error": err}
    return data
