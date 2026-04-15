"""
Shared layout components and styling for the Plotly Dash dashboard.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc


# ============================================================================
# Color palette
# ============================================================================
COLORS = {
    "github": "#238636",
    "github_light": "#2ea043",
    "spotify": "#1DB954",
    "spotify_dark": "#158a3e",
    "background": "#0d1117",
    "surface": "#161b22",
    "surface_2": "#21262d",
    "border": "#30363d",
    "text_primary": "#e6edf3",
    "text_secondary": "#8b949e",
    "accent": "#58a6ff",
    "danger": "#f85149",
    "warning": "#d29922",
}

CHART_LAYOUT = dict(
    paper_bgcolor=COLORS["surface"],
    plot_bgcolor=COLORS["surface"],
    font=dict(color=COLORS["text_primary"], family="monospace"),
    margin=dict(l=40, r=20, t=40, b=40),
    xaxis=dict(
        gridcolor=COLORS["border"],
        zerolinecolor=COLORS["border"],
        tickfont=dict(color=COLORS["text_secondary"]),
    ),
    yaxis=dict(
        gridcolor=COLORS["border"],
        zerolinecolor=COLORS["border"],
        tickfont=dict(color=COLORS["text_secondary"]),
    ),
    legend=dict(
        bgcolor=COLORS["surface_2"],
        bordercolor=COLORS["border"],
        font=dict(color=COLORS["text_primary"]),
    ),
)


# ============================================================================
# Navbar
# ============================================================================
def create_navbar():
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand(
                    [
                        html.Span("◈ ", style={"color": COLORS["accent"]}),
                        "Personal Analytics",
                    ],
                    href="/",
                    style={"color": COLORS["text_primary"], "fontFamily": "monospace", "fontWeight": "bold"},
                ),
                dbc.Nav(
                    [
                        dbc.NavItem(dbc.NavLink("Overview", href="/", active="exact",
                                                style={"color": COLORS["text_secondary"]})),
                        dbc.NavItem(dbc.NavLink("GitHub", href="/github", active="exact",
                                                style={"color": COLORS["text_secondary"]})),
                        dbc.NavItem(dbc.NavLink("Spotify", href="/spotify", active="exact",
                                                style={"color": COLORS["text_secondary"]})),
                    ],
                    navbar=True,
                ),
            ],
            fluid=True,
        ),
        color=COLORS["surface"],
        dark=True,
        style={"borderBottom": f"1px solid {COLORS['border']}"},
    )


# ============================================================================
# KPI Card
# ============================================================================
def kpi_card(title: str, value: str, subtitle: str = "", color: str = None, icon: str = ""):
    border_color = color or COLORS["border"]
    return dbc.Card(
        dbc.CardBody([
            html.P(
                [html.Span(icon + " " if icon else ""), title],
                className="mb-1",
                style={"color": COLORS["text_secondary"], "fontSize": "0.75rem", "textTransform": "uppercase",
                       "letterSpacing": "0.1em", "fontFamily": "monospace"},
            ),
            html.H3(
                value,
                style={"color": COLORS["text_primary"], "fontFamily": "monospace", "fontWeight": "bold",
                       "margin": "0"},
            ),
            html.P(
                subtitle,
                className="mb-0 mt-1",
                style={"color": COLORS["text_secondary"], "fontSize": "0.75rem"},
            ),
        ]),
        style={
            "backgroundColor": COLORS["surface"],
            "border": f"1px solid {border_color}",
            "borderRadius": "6px",
        },
    )


# ============================================================================
# Section Header
# ============================================================================
def section_header(title: str, color: str = None):
    return html.H5(
        title,
        style={
            "color": color or COLORS["text_primary"],
            "fontFamily": "monospace",
            "borderBottom": f"1px solid {COLORS['border']}",
            "paddingBottom": "8px",
            "marginBottom": "16px",
        },
    )


# ============================================================================
# Loading Spinner
# ============================================================================
def loading_spinner(component_id: str):
    return dcc.Loading(
        id=f"loading-{component_id}",
        type="circle",
        color=COLORS["accent"],
        children=html.Div(id=component_id),
    )


# ============================================================================
# Date Range Filter
# ============================================================================
def date_range_filter(component_id: str = "days-filter"):
    return dbc.ButtonGroup(
        [
            dbc.Button("7d", id=f"{component_id}-7", outline=True, size="sm",
                       color="secondary", n_clicks=0),
            dbc.Button("30d", id=f"{component_id}-30", outline=True, size="sm",
                       color="secondary", n_clicks=0, active=True),
            dbc.Button("90d", id=f"{component_id}-90", outline=True, size="sm",
                       color="secondary", n_clicks=0),
            dbc.Button("1yr", id=f"{component_id}-365", outline=True, size="sm",
                       color="secondary", n_clicks=0),
        ],
        size="sm",
    )


# ============================================================================
# Empty/Error state
# ============================================================================
def empty_state(message: str = "No data available"):
    return html.Div(
        [
            html.P("○", style={"fontSize": "2rem", "color": COLORS["text_secondary"]}),
            html.P(message, style={"color": COLORS["text_secondary"], "fontFamily": "monospace"}),
        ],
        style={"textAlign": "center", "padding": "40px"},
    )
