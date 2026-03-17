# utils/config.py

import os

def get_config():
    access_token = os.getenv("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzczODA5MTAwLCJpYXQiOjE3NzM3MjI3MDAsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2Mjk5MjMwIn0.UVhOeBb2aD_qKfYfmm69icPXAlY7TT5FAhu1lNu3imOdXJyvfj5MR6FC8kwgXbvLS2I2Ix77tU0UX7ho0YpTkQ")
    client_id = os.getenv("1106299230")
    errors = {}

    if not access_token:
        errors['ACCESS_TOKEN'] = "Missing ACCESS_TOKEN env"
    if not client_id:
        errors['CLIENT_ID'] = "Missing CLIENT_ID env"

    return {
        "ACCESS_TOKEN": access_token,
        "CLIENT_ID": client_id,
        "errors": errors
    }
