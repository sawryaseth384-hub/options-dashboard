import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_ai_signal(market_data):

    prompt = f"""
    You are a professional options trader AI.

    Analyze this data:
    {market_data}

    Give output in format:
    SIGNAL: BUY CALL / BUY PUT / WAIT
    STRIKE: suggested strike
    SL: stop loss
    TARGET: target
    REASON: short reasoning
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return response.choices[0].message.content
