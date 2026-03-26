from dhan_data.option_chain import get_option_chain as fetch_option_chain


def get_option_chain(security_id, expiry):
    try:
        data, err = fetch_option_chain(security_id, expiry=expiry, segment="NSE_INDEX")
        if err:
            return {"_error": err}
        return data
    except Exception as e:
        return {"_error": str(e)}
