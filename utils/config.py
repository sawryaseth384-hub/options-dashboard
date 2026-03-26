from utils.secrets import get_secret


def get_keys():
    return {
        "CLIENT_ID": get_secret("CLIENT_ID"),
        "PIN": get_secret("PIN"),
        "TOTP_SECRET": get_secret("TOTP_SECRET"),
    }
