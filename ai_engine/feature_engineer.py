import pandas as pd

def calculate_pcr(option_chain):

    call_oi = option_chain["call_oi"].sum()
    put_oi = option_chain["put_oi"].sum()

    pcr = put_oi / call_oi

    return round(pcr,2)
