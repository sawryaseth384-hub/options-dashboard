import os
import logging

print("🚀 APP FILE LOADED")

from dash import Dash, html, dcc, Input, Output

logging.basicConfig(level=logging.INFO)

PORT = int(os.environ.get("PORT", 8080))

app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("🔥 Railway Dash Test"),
    html.H2(id="output"),

    dcc.Interval(
        id="test-interval",
        interval=2000,
        n_intervals=0
    ),
])

@app.callback(
    Output("output", "children"),
    Input("test-interval", "n_intervals"),
)
def update(n):
    print("🔥 CALLBACK RUNNING:", n)
    return f"Counter: {n}"

print("🚀 DASH APP STARTED")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
