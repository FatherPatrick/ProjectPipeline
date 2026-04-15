"""
Overview dashboard page.
Combines GitHub and Spotify data into a single summary view.
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc

from dashboard.components import (
    COLORS, CHART_LAYOUT, kpi_card, section_header,
    date_range_filter, empty_state,
)
from dashboard import api_client


# ============================================================================
# Layout
# ============================================================================
def layout():
    return html.Div(
        [
            # Header
            html.Div(
                [
                    html.H4("Overview", style={"color": COLORS["text_primary"],
                                               "fontFamily": "monospace", "margin": 0}),
                    html.P("Combined activity across all sources",
                           style={"color": COLORS["text_secondary"], "margin": 0, "fontSize": "0.85rem"}),
                ],
                style={"marginBottom": "24px"},
            ),

            # Date range filter
            dbc.Row([
                dbc.Col([
                    html.Span("Time range: ", style={"color": COLORS["text_secondary"],
                                                     "fontFamily": "monospace", "fontSize": "0.8rem",
                                                     "marginRight": "8px"}),
                    date_range_filter("overview"),
                ], width="auto"),
            ], className="mb-4"),

            dcc.Store(id="overview-days", data=30),

            # KPI Row
            html.Div(id="overview-kpis", className="mb-4"),

            # Charts row
            dbc.Row([
                dbc.Col([
                    section_header("Productivity Score — Last 30 Days"),
                    dcc.Graph(id="overview-productivity-chart", config={"displayModeBar": False}),
                ], md=8),
                dbc.Col([
                    section_header("Activity Breakdown"),
                    dcc.Graph(id="overview-activity-donut", config={"displayModeBar": False}),
                ], md=4),
            ], className="mb-4"),

            # Heatmap row
            dbc.Row([
                dbc.Col([
                    section_header("GitHub Contribution Heatmap"),
                    dcc.Graph(id="overview-contribution-heatmap", config={"displayModeBar": False}),
                ], md=12),
            ], className="mb-4"),

            # Bottom row
            dbc.Row([
                dbc.Col([
                    section_header("Top Repos by Stars"),
                    html.Div(id="overview-top-repos"),
                ], md=6),
                dbc.Col([
                    section_header("Top Tracks This Month"),
                    html.Div(id="overview-top-tracks"),
                ], md=6),
            ]),
        ],
        style={"padding": "24px"},
    )


# ============================================================================
# Callbacks
# ============================================================================
@callback(
    Output("overview-days", "data"),
    [Input("overview-7", "n_clicks"),
     Input("overview-30", "n_clicks"),
     Input("overview-90", "n_clicks"),
     Input("overview-365", "n_clicks")],
    prevent_initial_call=False,
)
def update_days(n7, n30, n90, n365):
    from dash import ctx
    if not ctx.triggered_id:
        return 30
    mapping = {"overview-7": 7, "overview-30": 30, "overview-90": 90, "overview-365": 365}
    return mapping.get(ctx.triggered_id, 30)


@callback(Output("overview-kpis", "children"), Input("overview-days", "data"))
def update_kpis(days):
    overview = api_client.get_dashboard_overview(days)

    if not overview:
        return kpi_card("Status", "No Data", "Start the API and run the backfill script")

    gh = overview.get("github_stats", {})
    sp = overview.get("spotify_stats", {})
    trend = overview.get("productivity_trend", "stable")
    trend_icon = "↑" if trend == "up" else ("↓" if trend == "down" else "→")
    trend_color = COLORS["github"] if trend == "up" else (COLORS["danger"] if trend == "down" else COLORS["warning"])

    return dbc.Row([
        dbc.Col(kpi_card("Commits", f"{gh.get('total_commits', 0):,}",
                         f"Across {gh.get('total_repositories', 0)} repos",
                         COLORS["github"], "●"), md=3, className="mb-3"),
        dbc.Col(kpi_card("Day Streak", f"{gh.get('consecutive_days', 0)}d",
                         "consecutive contribution days",
                         COLORS["github_light"], "◆"), md=3, className="mb-3"),
        dbc.Col(kpi_card("Listening Time", f"{sp.get('total_listening_minutes', 0) // 60:,}h",
                         f"{sp.get('total_tracks_played', 0):,} tracks played",
                         COLORS["spotify"], "♪"), md=3, className="mb-3"),
        dbc.Col(kpi_card("Trend", f"{trend_icon} {trend.capitalize()}",
                         f"vs. previous {days // 2} days",
                         trend_color, "~"), md=3, className="mb-3"),
    ])


@callback(Output("overview-productivity-chart", "figure"), Input("overview-days", "data"))
def update_productivity_chart(days):
    aggregations = api_client.get_daily_aggregations(days)

    if not aggregations:
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT, title="No data")
        return fig

    df = pd.DataFrame(aggregations)
    df["aggregation_date"] = pd.to_datetime(df["aggregation_date"])
    df = df.sort_values("aggregation_date")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["aggregation_date"],
        y=df["github_commits"],
        name="GitHub Commits",
        line=dict(color=COLORS["github"], width=2),
        fill="tozeroy",
        fillcolor="rgba(35, 134, 54, 0.1)",
    ))
    fig.add_trace(go.Scatter(
        x=df["aggregation_date"],
        y=df["spotify_tracks_played"],
        name="Tracks Played",
        line=dict(color=COLORS["spotify"], width=2),
        yaxis="y2",
    ))
    fig.update_layout(
        **CHART_LAYOUT,
        yaxis=dict(**CHART_LAYOUT.get("yaxis", {}), title="Commits", titlefont=dict(color=COLORS["github"])),
        yaxis2=dict(
            overlaying="y", side="right", title="Tracks",
            titlefont=dict(color=COLORS["spotify"]),
            tickfont=dict(color=COLORS["text_secondary"]),
            gridcolor=COLORS["border"],
        ),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1),
    )
    return fig


@callback(Output("overview-activity-donut", "figure"), Input("overview-days", "data"))
def update_activity_donut(days):
    overview = api_client.get_dashboard_overview(days)

    if not overview:
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT)
        return fig

    gh = overview.get("github_stats", {})
    sp = overview.get("spotify_stats", {})

    labels = ["GitHub Commits", "Listening Hours", "Repos Touched"]
    values = [
        gh.get("total_commits", 0),
        sp.get("total_listening_minutes", 0) // 60,
        gh.get("total_repositories", 0),
    ]
    colors = [COLORS["github"], COLORS["spotify"], COLORS["accent"]]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color=COLORS["surface"], width=2)),
        textfont=dict(color=COLORS["text_primary"]),
    ))
    fig.update_layout(**CHART_LAYOUT, showlegend=True)
    return fig


@callback(Output("overview-contribution-heatmap", "figure"), Input("overview-days", "data"))
def update_heatmap(days):
    contributions = api_client.get_github_contributions(min(days, 365))

    if not contributions:
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT, title="No contribution data")
        return fig

    df = pd.DataFrame(contributions)
    df["contribution_date"] = pd.to_datetime(df["contribution_date"])
    df["week"] = df["contribution_date"].dt.isocalendar().week
    df["weekday"] = df["contribution_date"].dt.weekday
    df["date_str"] = df["contribution_date"].dt.strftime("%b %d, %Y")

    weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    fig = go.Figure(go.Heatmap(
        x=df["week"],
        y=df["weekday"],
        z=df["commit_count"],
        text=df["date_str"] + ": " + df["commit_count"].astype(str) + " commits",
        hovertemplate="%{text}<extra></extra>",
        colorscale=[
            [0, COLORS["surface_2"]],
            [0.25, "#0e4429"],
            [0.5, "#006d32"],
            [0.75, COLORS["github_light"]],
            [1, "#56d364"],
        ],
        showscale=False,
        xgap=3,
        ygap=3,
    ))

    fig.update_layout(
        **CHART_LAYOUT,
        yaxis=dict(
            tickvals=list(range(7)),
            ticktext=weekday_labels,
            tickfont=dict(color=COLORS["text_secondary"], size=11),
            gridcolor="transparent",
        ),
        xaxis=dict(showgrid=False, showticklabels=False),
        height=180,
        margin=dict(l=40, r=10, t=10, b=20),
    )
    return fig


@callback(Output("overview-top-repos", "children"), Input("overview-days", "data"))
def update_top_repos(_days):
    repos = api_client.get_github_repositories()

    if not repos or not repos.get("items"):
        return empty_state("No repositories found")

    rows = []
    for repo in repos["items"][:6]:
        lang = repo.get("language") or "—"
        lang_color = COLORS["github"] if lang != "—" else COLORS["text_secondary"]
        rows.append(
            html.Div([
                html.Div([
                    html.Span(repo["repo_name"], style={"color": COLORS["accent"],
                                                        "fontFamily": "monospace", "fontSize": "0.85rem"}),
                    html.Span(f"  {repo.get('stars', 0)} ★",
                              style={"color": COLORS["warning"], "fontSize": "0.75rem", "marginLeft": "8px"}),
                ]),
                html.Span(lang, style={"color": lang_color, "fontSize": "0.75rem",
                                       "fontFamily": "monospace"}),
            ], style={
                "display": "flex", "justifyContent": "space-between", "alignItems": "center",
                "padding": "8px 12px", "borderBottom": f"1px solid {COLORS['border']}",
            })
        )

    return html.Div(rows, style={"backgroundColor": COLORS["surface"],
                                 "border": f"1px solid {COLORS['border']}", "borderRadius": "6px"})


@callback(Output("overview-top-tracks", "children"), Input("overview-days", "data"))
def update_top_tracks(days):
    tracks = api_client.get_top_tracks(days=days, limit=6)

    if not tracks:
        return empty_state("No listening data found")

    rows = []
    for i, track in enumerate(tracks[:6], 1):
        rows.append(
            html.Div([
                html.Span(f"{i}. ", style={"color": COLORS["text_secondary"],
                                           "fontSize": "0.75rem", "fontFamily": "monospace", "minWidth": "20px"}),
                html.Span(track["name"][:30], style={"color": COLORS["text_primary"],
                                                     "fontFamily": "monospace", "fontSize": "0.85rem",
                                                     "flex": 1}),
                html.Span(f"{track.get('play_count', 0)}×",
                          style={"color": COLORS["spotify"], "fontSize": "0.75rem"}),
            ], style={
                "display": "flex", "alignItems": "center", "gap": "8px",
                "padding": "8px 12px", "borderBottom": f"1px solid {COLORS['border']}",
            })
        )

    return html.Div(rows, style={"backgroundColor": COLORS["surface"],
                                 "border": f"1px solid {COLORS['border']}", "borderRadius": "6px"})
