from utils.secrets import get_secret


def get_keys():
    return {
        "CLIENT_ID": get_secret("CLIENT_ID"),
        "DHAN_ACCESS_TOKEN": get_secret("DHAN_ACCESS_TOKEN"),
    }
