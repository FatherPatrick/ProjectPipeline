"""
GitHub dashboard page.
Detailed GitHub activity visualizations.
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
            html.Div([
                html.H4("GitHub Activity", style={"color": COLORS["github"],
                                                   "fontFamily": "monospace", "margin": 0}),
                html.P("Commits, repositories, and contribution patterns",
                       style={"color": COLORS["text_secondary"], "margin": 0, "fontSize": "0.85rem"}),
            ], style={"marginBottom": "24px"}),

            dbc.Row([
                dbc.Col([
                    html.Span("Time range: ", style={"color": COLORS["text_secondary"],
                                                     "fontFamily": "monospace", "fontSize": "0.8rem",
                                                     "marginRight": "8px"}),
                    date_range_filter("github"),
                ], width="auto"),
            ], className="mb-4"),

            dcc.Store(id="github-days", data=30),

            # KPI Row
            html.Div(id="github-kpis", className="mb-4"),

            # Commits over time
            dbc.Row([
                dbc.Col([
                    section_header("Commits Over Time", COLORS["github"]),
                    dcc.Graph(id="github-commits-chart", config={"displayModeBar": False}),
                ], md=8),
                dbc.Col([
                    section_header("Language Breakdown", COLORS["github"]),
                    dcc.Graph(id="github-languages-chart", config={"displayModeBar": False}),
                ], md=4),
            ], className="mb-4"),

            # Code changes
            dbc.Row([
                dbc.Col([
                    section_header("Code Changes (Additions vs Deletions)", COLORS["github"]),
                    dcc.Graph(id="github-code-changes-chart", config={"displayModeBar": False}),
                ], md=12),
            ], className="mb-4"),

            # Repository table
            dbc.Row([
                dbc.Col([
                    section_header("Repositories", COLORS["github"]),
                    html.Div(id="github-repos-table"),
                ], md=12),
            ]),
        ],
        style={"padding": "24px"},
    )


# ============================================================================
# Callbacks
# ============================================================================
@callback(
    Output("github-days", "data"),
    [Input("github-7", "n_clicks"),
     Input("github-30", "n_clicks"),
     Input("github-90", "n_clicks"),
     Input("github-365", "n_clicks")],
    prevent_initial_call=False,
)
def update_days(n7, n30, n90, n365):
    from dash import ctx
    if not ctx.triggered_id:
        return 30
    mapping = {"github-7": 7, "github-30": 30, "github-90": 90, "github-365": 365}
    return mapping.get(ctx.triggered_id, 30)


@callback(Output("github-kpis", "children"), Input("github-days", "data"))
def update_kpis(days):
    stats = api_client.get_github_stats(days)

    if not stats:
        return empty_state("API not reachable. Ensure the API is running.")

    return dbc.Row([
        dbc.Col(kpi_card("Total Commits", f"{stats.get('total_commits', 0):,}",
                         f"in last {days} days", COLORS["github"], "●"), md=3, className="mb-3"),
        dbc.Col(kpi_card("Repositories", f"{stats.get('total_repositories', 0)}",
                         "owned repositories", COLORS["github_light"], "◈"), md=3, className="mb-3"),
        dbc.Col(kpi_card("Lines Added", f"+{stats.get('total_additions', 0):,}",
                         f"−{stats.get('total_deletions', 0):,} deleted",
                         COLORS["accent"], "≡"), md=3, className="mb-3"),
        dbc.Col(kpi_card("Top Language", stats.get("most_used_language", "—"),
                         f"{stats.get('consecutive_days', 0)}d streak",
                         COLORS["warning"], "◇"), md=3, className="mb-3"),
    ])


@callback(Output("github-commits-chart", "figure"), Input("github-days", "data"))
def update_commits_chart(days):
    contributions = api_client.get_github_contributions(days)

    if not contributions:
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT, title="No data")
        return fig

    df = pd.DataFrame(contributions)
    df["contribution_date"] = pd.to_datetime(df["contribution_date"])
    df = df.sort_values("contribution_date")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["contribution_date"],
        y=df["commit_count"],
        marker=dict(
            color=df["commit_count"],
            colorscale=[[0, COLORS["surface_2"]], [0.3, "#0e4429"],
                        [0.6, COLORS["github"]], [1, "#56d364"]],
            showscale=False,
        ),
        hovertemplate="<b>%{x|%b %d}</b><br>%{y} commits<extra></extra>",
    ))
    # Rolling average
    if len(df) >= 7:
        df["rolling_avg"] = df["commit_count"].rolling(7, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=df["contribution_date"],
            y=df["rolling_avg"],
            name="7-day avg",
            line=dict(color=COLORS["accent"], width=2, dash="dot"),
            hoverinfo="skip",
        ))

    fig.update_layout(**{
        **CHART_LAYOUT,
        "showlegend": True,
        "legend": dict(**CHART_LAYOUT.get("legend", {}), orientation="h", y=1.1),
    })
    return fig


@callback(Output("github-languages-chart", "figure"), Input("github-days", "data"))
def update_languages_chart(days):
    languages = api_client.get_github_languages(days)

    if not languages:
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT)
        return fig

    # Drop unknown
    languages = {k: v for k, v in languages.items() if k and k != "None"}
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:8]
    labels, values = zip(*sorted_langs) if sorted_langs else ([], [])

    palette = [COLORS["github"], COLORS["accent"], COLORS["spotify"], COLORS["warning"],
               "#bc8cff", "#ff7b72", "#ffa657", "#3fb950"]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker=dict(colors=palette[:len(labels)], line=dict(color=COLORS["surface"], width=2)),
        textfont=dict(color=COLORS["text_primary"], size=11),
        textinfo="label+percent",
        insidetextorientation="auto",
    ))
    fig.update_layout(**CHART_LAYOUT, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
    return fig


@callback(Output("github-code-changes-chart", "figure"), Input("github-days", "data"))
def update_code_changes(days):
    contributions = api_client.get_github_contributions(days)

    if not contributions:
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT, title="No data")
        return fig

    df = pd.DataFrame(contributions)
    df["contribution_date"] = pd.to_datetime(df["contribution_date"])
    df = df.sort_values("contribution_date")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["contribution_date"],
        y=df["total_additions"],
        name="Additions",
        marker_color=COLORS["github"],
        hovertemplate="<b>%{x|%b %d}</b><br>+%{y} lines<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=df["contribution_date"],
        y=[-v for v in df["total_deletions"]],
        name="Deletions",
        marker_color=COLORS["danger"],
        hovertemplate="<b>%{x|%b %d}</b><br>−%{customdata} lines<extra></extra>",
        customdata=df["total_deletions"],
    ))
    fig.update_layout(**{
        **CHART_LAYOUT,
        "barmode": "relative",
        "showlegend": True,
        "legend": dict(**CHART_LAYOUT.get("legend", {}), orientation="h", y=1.1),
    })
    return fig


@callback(Output("github-repos-table", "children"), Input("github-days", "data"))
def update_repos_table(_days):
    repos_data = api_client.get_github_repositories()

    if not repos_data or not repos_data.get("items"):
        return empty_state("No repositories found")

    header = html.Div([
        html.Span("Repository", style={"flex": 3, "color": COLORS["text_secondary"],
                                       "fontSize": "0.75rem", "textTransform": "uppercase"}),
        html.Span("Language", style={"flex": 1, "color": COLORS["text_secondary"],
                                     "fontSize": "0.75rem", "textTransform": "uppercase"}),
        html.Span("Stars", style={"flex": 1, "color": COLORS["text_secondary"],
                                  "fontSize": "0.75rem", "textTransform": "uppercase", "textAlign": "right"}),
        html.Span("Forks", style={"flex": 1, "color": COLORS["text_secondary"],
                                  "fontSize": "0.75rem", "textTransform": "uppercase", "textAlign": "right"}),
        html.Span("Visibility", style={"flex": 1, "color": COLORS["text_secondary"],
                                       "fontSize": "0.75rem", "textTransform": "uppercase", "textAlign": "right"}),
    ], style={"display": "flex", "padding": "8px 12px",
              "borderBottom": f"1px solid {COLORS['border']}"})

    rows = [header]
    for repo in repos_data["items"]:
        lang = repo.get("language") or "—"
        visibility = "Private" if repo.get("is_private") else "Public"
        vis_color = COLORS["text_secondary"] if visibility == "Private" else COLORS["github_light"]
        fork_badge = " (fork)" if repo.get("is_fork") else ""

        rows.append(html.Div([
            html.A(repo["repo_name"] + fork_badge,
                   href=repo["url"], target="_blank",
                   style={"flex": 3, "color": COLORS["accent"], "fontFamily": "monospace",
                          "fontSize": "0.85rem", "textDecoration": "none"}),
            html.Span(lang, style={"flex": 1, "color": COLORS["text_primary"],
                                   "fontFamily": "monospace", "fontSize": "0.8rem"}),
            html.Span(f"{repo.get('stars', 0)} ★", style={"flex": 1, "color": COLORS["warning"],
                                                           "fontSize": "0.8rem", "textAlign": "right"}),
            html.Span(str(repo.get("forks", 0)), style={"flex": 1, "color": COLORS["text_secondary"],
                                                         "fontSize": "0.8rem", "textAlign": "right"}),
            html.Span(visibility, style={"flex": 1, "color": vis_color,
                                         "fontSize": "0.75rem", "textAlign": "right"}),
        ], style={"display": "flex", "alignItems": "center", "padding": "8px 12px",
                  "borderBottom": f"1px solid {COLORS['border']}"}))

    return html.Div(rows, style={"backgroundColor": COLORS["surface"],
                                 "border": f"1px solid {COLORS['border']}", "borderRadius": "6px"})
