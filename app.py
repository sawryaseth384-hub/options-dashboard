import os
import logging
from dash import Dash, html, dcc, Input, Output

# ✅ LOGGING FIX (MOST IMPORTANT)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gunicorn.error")

PORT = int(os.environ.get("PORT", 8080))

app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("🔥 Railway Dash Test"),
    html.H2(id="output"),
    dcc.Interval(id="test-interval", interval=2000, n_intervals=0),
])

@app.callback(
    Output("output", "children"),
    Input("test-interval", "n_intervals"),
)
def update(n):
    logger.info(f"🔥 CALLBACK RUNNING: {n}")
    return f"Counter: {n}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
