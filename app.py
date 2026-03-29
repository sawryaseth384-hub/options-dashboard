import os
import logging
from dash import Dash, html, dcc, Input, Output

# ---------- LOGGING ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PORT = int(os.environ.get("PORT", 3000))

# ---------- APP ----------
app = Dash(
    __name__,
    suppress_callback_exceptions=True
)
server = app.server

# ---------- LAYOUT ----------
app.layout = html.Div([
    html.H1("🔥 Railway Dash Test"),
    html.H2(id="output"),
    
    dcc.Interval(
        id="test-interval",
        interval=2000,  # 2 sec
        n_intervals=0
    ),
])

# ---------- CALLBACK ----------
@app.callback(
    Output("output", "children"),
    Input("test-interval", "n_intervals"),
)
def update(n):
    print("🔥 CALLBACK RUNNING:", n)
    logging.info(f"CALLBACK RUNNING: {n}")
    return f"Counter: {n}"

# ---------- RUN ----------
if __name__ == "__main__":
    print("🚀 APP STARTED")
    app.run(host="0.0.0.0", port=PORT, debug=False)
