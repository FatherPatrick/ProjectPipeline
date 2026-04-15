"""
Main Plotly Dash application entry point.
Multi-page dashboard for GitHub and Spotify analytics.

Run with: poetry run python -m dashboard.app
"""
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output

from pipeline.config import get_settings
from dashboard.components import COLORS, create_navbar
from dashboard.pages import overview, github, spotify

settings = get_settings()

# ============================================================================
# App initialization
# ============================================================================
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap",
    ],
    suppress_callback_exceptions=True,
    title="Personal Analytics Dashboard",
    update_title=None,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server  # Expose Flask server for production WSGI

# ============================================================================
# Global layout (persistent across all pages)
# ============================================================================
app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        create_navbar(),
        html.Div(id="page-content"),
    ],
    style={
        "backgroundColor": COLORS["background"],
        "minHeight": "100vh",
        "fontFamily": "'JetBrains Mono', monospace",
    },
)

# ============================================================================
# Router callback
# ============================================================================
@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def render_page(pathname: str):
    """Route URL to the appropriate page layout."""
    if pathname == "/github":
        return github.layout()
    elif pathname == "/spotify":
        return spotify.layout()
    else:
        return overview.layout()  # Default: overview


# ============================================================================
# Entry point
# ============================================================================
if __name__ == "__main__":
    app.run(
        host=settings.dashboard_host,
        port=settings.dashboard_port,
        debug=settings.debug,
    )
