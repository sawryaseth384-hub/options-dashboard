import os
import logging
from dash import Dash, html, dcc, Input, Output

# Logging fix
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gunicorn.error")

PORT = int(os.environ.get("PORT", 8080))

app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("🔥 FINAL TEST"),
    
    html.Button("CLICK ME", id="btn"),   # 👈 BUTTON ADD
    
    html.H2(id="output"),

    dcc.Interval(
        id="interval",
        interval=2000,
        n_intervals=0
    ),
])

@app.callback(
    Output("output", "children"),
    Input("interval", "n_intervals"),
    Input("btn", "n_clicks"),
)
def update(n, clicks):
    logger.info(f"🔥 CALLBACK RUNNING: {n}, clicks: {clicks}")
    return f"Counter: {n}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
