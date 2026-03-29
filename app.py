import os
import logging
from dash import Dash, html, dcc, Input, Output

# ---------- LOGGING ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gunicorn.error")

print("🚀 APP FILE IMPORTED")  # Gunicorn load check

# ---------- ENV ----------
PORT = int(os.environ.get("PORT", 8080))

# ---------- APP ----------
app = Dash(__name__)
server = app.server  # 🔥 REQUIRED for Railway

# ---------- LAYOUT ----------
app.layout = html.Div([
    html.H1("🔥 Railway Dash LIVE"),
    html.H2(id="output"),
    
    dcc.Interval(
        id="interval",
        interval=2000,   # 2 sec
        n_intervals=0
    ),
])

print("✅ LAYOUT LOADED")

# ---------- CALLBACK ----------
@app.callback(
    Output("output", "children"),
    Input("interval", "n_intervals"),
)
def update(n):
    logger.info(f"🔥 CALLBACK RUNNING: {n}")
    return f"Counter: {n}"

print("✅ CALLBACK REGISTERED")

# ---------- RUN (local only) ----------
if __name__ == "__main__":
    print("🚀 LOCAL RUN")
    app.run(host="0.0.0.0", port=PORT, debug=False)
