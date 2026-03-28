import os


def get_secret(key, default=None):
    return os.getenv(key, default)
