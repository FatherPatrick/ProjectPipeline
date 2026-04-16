"""
Spotify dashboard page.
Detailed listening history and music preference visualizations.
"""
import plotly.graph_objects as go
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
                html.H4("Spotify Listening", style={"color": COLORS["spotify"],
                                                     "fontFamily": "monospace", "margin": 0}),
                html.P("Track listening habits, top artists, and music patterns",
                       style={"color": COLORS["text_secondary"], "margin": 0, "fontSize": "0.85rem"}),
            ], style={"marginBottom": "24px"}),

            dbc.Row([
                dbc.Col([
                    html.Span("Time range: ", style={"color": COLORS["text_secondary"],
                                                     "fontFamily": "monospace", "fontSize": "0.8rem",
                                                     "marginRight": "8px"}),
                    date_range_filter("spotify"),
                ], width="auto"),
            ], className="mb-4"),

            dcc.Store(id="spotify-days", data=30),

            # KPI Row
            html.Div(id="spotify-kpis", className="mb-4"),

            # Top charts row
            dbc.Row([
                dbc.Col([
                    section_header("Top Tracks", COLORS["spotify"]),
                    html.Div(id="spotify-top-tracks"),
                ], md=6),
                dbc.Col([
                    section_header("Top Artists", COLORS["spotify"]),
                    dcc.Graph(id="spotify-top-artists-chart", config={"displayModeBar": False}),
                ], md=6),
            ], className="mb-4"),

            # Listening pattern charts
            dbc.Row([
                dbc.Col([
                    section_header("Listening Activity by Hour", COLORS["spotify"]),
                    dcc.Graph(id="spotify-hourly-chart", config={"displayModeBar": False}),
                ], md=6),
                dbc.Col([
                    section_header("Genre Distribution", COLORS["spotify"]),
                    dcc.Graph(id="spotify-genre-chart", config={"displayModeBar": False}),
                ], md=6),
            ], className="mb-4"),

            # Listening over time
            dbc.Row([
                dbc.Col([
                    section_header("Daily Listening Minutes", COLORS["spotify"]),
                    dcc.Graph(id="spotify-daily-listening-chart", config={"displayModeBar": False}),
                ], md=12),
            ]),
        ],
        style={"padding": "24px"},
    )


# ============================================================================
# Callbacks
# ============================================================================
@callback(
    Output("spotify-days", "data"),
    [Input("spotify-7", "n_clicks"),
     Input("spotify-30", "n_clicks"),
     Input("spotify-90", "n_clicks"),
     Input("spotify-365", "n_clicks")],
    prevent_initial_call=False,
)
def update_days(n7, n30, n90, n365):
    from dash import ctx
    if not ctx.triggered_id:
        return 30
    mapping = {"spotify-7": 7, "spotify-30": 30, "spotify-90": 90, "spotify-365": 365}
    return mapping.get(ctx.triggered_id, 30)


@callback(Output("spotify-kpis", "children"), Input("spotify-days", "data"))
def update_kpis(days):
    stats = api_client.get_spotify_stats(days)

    if not stats:
        return empty_state("API not reachable. Ensure the API is running.")

    hours = stats.get("total_listening_minutes", 0) // 60
    avg_min = stats.get("average_daily_listening", 0)

    return dbc.Row([
        dbc.Col(kpi_card("Tracks Played", f"{stats.get('total_tracks_played', 0):,}",
                         f"in last {days} days", COLORS["spotify"], "♪"), md=3, className="mb-3"),
        dbc.Col(kpi_card("Hours Listened", f"{hours:,}h",
                         f"{avg_min:.0f} min/day avg", COLORS["spotify_dark"], "▶"), md=3, className="mb-3"),
        dbc.Col(kpi_card("Unique Artists", f"{stats.get('unique_artists', 0):,}",
                         f"{stats.get('unique_tracks', 0):,} unique tracks",
                         COLORS["accent"], "♫"), md=3, className="mb-3"),
        dbc.Col(kpi_card("Listening Streak", f"{stats.get('listening_streak', 0)}d",
                         "consecutive days", COLORS["warning"], "◆"), md=3, className="mb-3"),
    ])


@callback(Output("spotify-top-tracks", "children"), Input("spotify-days", "data"))
def update_top_tracks(days):
    tracks = api_client.get_top_tracks(days=days, limit=10)

    if not tracks:
        return empty_state("No listening data found")

    max_plays = max((t.get("play_count", 1) for t in tracks), default=1)

    rows = []
    for i, track in enumerate(tracks, 1):
        play_count = track.get("play_count", 0)
        bar_pct = (play_count / max_plays) * 100
        duration_sec = track.get("duration_ms", 0) // 1000
        duration_str = f"{duration_sec // 60}:{duration_sec % 60:02d}"

        rows.append(html.Div([
            html.Span(f"{i:2d}", style={"color": COLORS["text_secondary"], "fontFamily": "monospace",
                                         "fontSize": "0.75rem", "minWidth": "24px"}),
            html.Div([
                html.Div([
                    html.Span(track["name"][:35] + ("…" if len(track["name"]) > 35 else ""),
                              style={"color": COLORS["text_primary"], "fontFamily": "monospace",
                                     "fontSize": "0.82rem", "fontWeight": "bold"}),
                    html.Br(),
                    html.Span(duration_str, style={"color": COLORS["text_secondary"], "fontSize": "0.72rem"}),
                ], style={"flex": 1}),
                html.Div([
                    html.Div(style={
                        "height": "4px", "width": f"{bar_pct}%",
                        "backgroundColor": COLORS["spotify"], "borderRadius": "2px",
                        "marginBottom": "2px",
                    }),
                    html.Span(f"{play_count}×", style={"color": COLORS["spotify"],
                                                        "fontSize": "0.75rem", "fontFamily": "monospace"}),
                ], style={"minWidth": "80px"}),
            ], style={"display": "flex", "alignItems": "center", "flex": 1, "gap": "12px"}),
        ], style={"display": "flex", "alignItems": "center", "gap": "8px",
                  "padding": "10px 12px", "borderBottom": f"1px solid {COLORS['border']}"}))

    return html.Div(rows, style={"backgroundColor": COLORS["surface"],
                                 "border": f"1px solid {COLORS['border']}", "borderRadius": "6px"})


@callback(Output("spotify-top-artists-chart", "figure"), Input("spotify-days", "data"))
def update_top_artists(_days):
    artists = api_client.get_top_artists(limit=10)

    if not artists:
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT, title="No data")
        return fig

    names = [a["name"] for a in reversed(artists)]
    popularity = [a.get("popularity", 0) for a in reversed(artists)]

    fig = go.Figure(go.Bar(
        x=popularity,
        y=names,
        orientation="h",
        marker=dict(
            color=popularity,
            colorscale=[[0, COLORS["spotify_dark"]], [1, COLORS["spotify"]]],
            showscale=False,
        ),
        hovertemplate="<b>%{y}</b><br>Popularity: %{x}<extra></extra>",
    ))
    fig.update_layout(
        **CHART_LAYOUT,
        xaxis=dict(**CHART_LAYOUT.get("xaxis", {}), title="Popularity Score"),
        margin=dict(l=120, r=20, t=20, b=40),
        height=320,
    )
    return fig


@callback(Output("spotify-hourly-chart", "figure"), Input("spotify-days", "data"))
def update_hourly_chart(days):
    hourly = api_client.get_listening_by_hour(days)

    if not hourly:
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT, title="No data")
        return fig

    hours = list(range(24))
    counts = [hourly.get(str(h), 0) for h in hours]
    labels = [f"{h:02d}:00" for h in hours]

    # Color by time of day
    time_colors = []
    for h in hours:
        if 6 <= h < 12:
            time_colors.append("#ffa657")   # Morning - orange
        elif 12 <= h < 18:
            time_colors.append(COLORS["accent"])   # Afternoon - blue
        elif 18 <= h < 23:
            time_colors.append(COLORS["spotify"])  # Evening - green
        else:
            time_colors.append(COLORS["surface_2"])  # Night - dark

    fig = go.Figure(go.Bar(
        x=labels,
        y=counts,
        marker_color=time_colors,
        hovertemplate="<b>%{x}</b><br>%{y} tracks<extra></extra>",
    ))
    fig.update_layout(**{
        **CHART_LAYOUT,
        "xaxis": {
            **CHART_LAYOUT.get("xaxis", {}),
            "tickangle": 45,
            "tickfont": {
                **CHART_LAYOUT.get("xaxis", {}).get("tickfont", {}),
                "size": 10,
                "color": COLORS["text_secondary"],
            },
        },
        "annotations": [
            dict(x=9, y=max(counts) * 1.05 if counts else 1, text="Morning",
                 showarrow=False, font=dict(color="#ffa657", size=10)),
            dict(x=15, y=max(counts) * 1.05 if counts else 1, text="Afternoon",
                 showarrow=False, font=dict(color=COLORS["accent"], size=10)),
            dict(x=20, y=max(counts) * 1.05 if counts else 1, text="Evening",
                 showarrow=False, font=dict(color=COLORS["spotify"], size=10)),
        ],
    })
    return fig


@callback(Output("spotify-genre-chart", "figure"), Input("spotify-days", "data"))
def update_genre_chart(_days):
    artists = api_client.get_top_artists(limit=50)

    if not artists:
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT)
        return fig

    genre_counts = {}
    for artist in artists:
        for genre in artist.get("genres", []):
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

    if not genre_counts:
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT, title="No genre data")
        return fig

    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    labels, values = zip(*sorted_genres)

    palette = [COLORS["spotify"], COLORS["accent"], COLORS["github"], COLORS["warning"],
               "#bc8cff", "#ff7b72", "#ffa657", "#3fb950", "#58a6ff", "#f78166"]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.45,
        marker=dict(colors=palette[:len(labels)], line=dict(color=COLORS["surface"], width=2)),
        textfont=dict(color=COLORS["text_primary"], size=10),
        textinfo="label+percent",
        insidetextorientation="auto",
    ))
    fig.update_layout(**CHART_LAYOUT, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
    return fig


@callback(Output("spotify-daily-listening-chart", "figure"), Input("spotify-days", "data"))
def update_daily_listening_chart(days):
    aggregations = api_client.get_daily_aggregations(days)

    if not aggregations:
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT, title="No data")
        return fig

    df = pd.DataFrame(aggregations)
    df["aggregation_date"] = pd.to_datetime(df["aggregation_date"])
    df = df.sort_values("aggregation_date")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["aggregation_date"],
        y=df["spotify_listening_minutes"],
        name="Listening Minutes",
        marker=dict(
            color=df["spotify_listening_minutes"],
            colorscale=[[0, COLORS["surface_2"]], [0.4, COLORS["spotify_dark"]], [1, COLORS["spotify"]]],
            showscale=False,
        ),
        hovertemplate="<b>%{x|%b %d}</b><br>%{y} minutes<extra></extra>",
    ))
    if len(df) >= 7:
        df["rolling_avg"] = df["spotify_listening_minutes"].rolling(7, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=df["aggregation_date"],
            y=df["rolling_avg"],
            name="7-day avg",
            line=dict(color=COLORS["accent"], dash="dot", width=2),
            hoverinfo="skip",
        ))

    fig.update_layout(**{
        **CHART_LAYOUT,
        "showlegend": True,
        "legend": dict(**CHART_LAYOUT.get("legend", {}), orientation="h", y=1.1),
        "yaxis": dict(**CHART_LAYOUT.get("yaxis", {}), title="Minutes"),
    })
    return fig
