def generate_signal(pcr):

    if pcr > 1.2:
        return "BULLISH"

    elif pcr < 0.8:
        return "BEARISH"

    else:
        return "SIDEWAYS"
