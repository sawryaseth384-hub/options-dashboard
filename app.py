import os
import logging
from dash import Dash, html, dcc, Input, Output

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gunicorn.error")

print("🚀 APP FILE IMPORTED")

PORT = int(os.environ.get("PORT", 8080))

app = Dash(
    __name__,
    serve_locally=True   # 🔥 FIX
)
server = app.server

app.layout = html.Div([
    html.H1("🔥 Railway Dash FINAL"),
    html.H2(id="output"),
    dcc.Interval(id="interval", interval=2000, n_intervals=0),
])

print("✅ LAYOUT LOADED")

@app.callback(
    Output("output", "children"),
    Input("interval", "n_intervals"),
)
def update(n):
    logger.info(f"🔥 CALLBACK RUNNING: {n}")
    return f"Counter: {n}"

print("✅ CALLBACK REGISTERED")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
