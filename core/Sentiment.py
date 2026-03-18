# core/sentiment.py

def get_sentiment(data):

    fii = data.get("FII", 0)
    pcr = data.get("PCR", 1)

    if fii > 0 and pcr > 1:
        return "🟢 BULLISH"
    elif fii < 0 and pcr < 1:
        return "🔴 BEARISH"
    else:
        return "🟡 SIDEWAYS"
