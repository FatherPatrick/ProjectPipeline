# Personal Data Analytics Dashboard

A full-stack data pipeline that aggregates personal data from GitHub, Spotify, and Steam APIs, processes it, stores it in a database, and visualizes it through an interactive web dashboard.

## Features

- **Multi-source Data Aggregation**: Collects data from GitHub (commits, contributions), Spotify (listening history), and Steam (gaming activity)
- **Automated Data Pipeline**: Scheduled jobs that fetch and process data weekly
- **Real-time Visualizations**: Interactive dashboard with charts, heatmaps, and trends
- **Professional Backend**: FastAPI-powered REST API
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Production-ready**: Docker containerization and cloud deployment

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.10+ |
| **API Clients** | requests |
| **Scheduler** | APScheduler |
| **Database** | PostgreSQL + SQLAlchemy |
| **Backend API** | FastAPI |
| **Dashboard** | Plotly Dash |
| **Dependency Management** | Poetry |
| **Deployment** | Docker + Railway |

## Project Structure

```
ProjectPipeline/
├── src/
│   ├── pipeline/              # Core pipeline logic
│   │   ├── config.py          # Configuration management
│   │   ├── database.py        # SQLAlchemy setup
│   │   └── models.py          # ORM models
│   ├── collectors/            # Data source collectors
│   │   ├── github_client.py   # GitHub API client
│   │   ├── spotify_client.py  # Spotify API client
│   │   └── steam_client.py    # (Future) Steam API client
│   ├── pipeline_jobs/         # Scheduled jobs
│   ├── api/                   # FastAPI backend
│   └── dashboard/             # Plotly Dash frontend
├── tests/                      # Automated pytest suite
├── scripts/                    # Manual utility and smoke-check scripts
│   ├── init_db.py             # Database initialization
│   ├── backfill_data.py       # Historical data load
│   └── check_collectors.py    # Manual API credential smoke check
└── pyproject.toml             # Poetry dependencies
```

## Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Docker & Docker Compose (optional, for containerized Postgres)
- Poetry (for dependency management)

## Setup Instructions

### 1. Install Dependencies

```bash
# Install Poetry (if not already installed)
pip install poetry

# Install project dependencies
poetry install
```

### 2. Configure Environment

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
```

Then edit `.env` and fill in:
- `GITHUB_TOKEN`: [Create a Personal Access Token](https://github.com/settings/tokens)
- `GITHUB_USERNAME`: Your GitHub username
- `SPOTIFY_CLIENT_ID` & `SPOTIFY_CLIENT_SECRET`: [Get from Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- `DATABASE_URL`: PostgreSQL connection string

### 3. Set Up Database

**Option A: Using Docker (Recommended)**

```bash
# Start PostgreSQL in Docker
docker-compose up -d

# This starts both Postgres and PgAdmin (admin UI at http://localhost:5050)
```

**Option B: Local PostgreSQL**

Make sure PostgreSQL is running and the database exists.

### 4. Initialize Database Tables

```bash
poetry run python scripts/init_db.py
```

You should see:
```
✓ Database connection successful
✓ Creating database tables...
✓ Database tables created successfully
```

## Running the Application

### Start the Data Collection Pipeline

```bash
poetry run python -m pipeline_jobs.scheduler
```

This starts the APScheduler that runs data collection jobs on a weekly schedule.

### Start the FastAPI Backend

In another terminal:

```bash
poetry run python -m api.main
```

The API will be available at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Start the Dashboard

In another terminal:

```bash
poetry run python -m dashboard.app
```

The dashboard will be available at `http://localhost:8050`

## Data Models

### User
- Stores user credentials and OAuth tokens for GitHub and Spotify

### GitHub Models
- **GitHubRepository**: Repository metadata
- **GitHubCommit**: Individual commits with stats
- **GitHubContribution**: Daily contribution aggregates

### Spotify Models
- **SpotifyTrack**: Track metadata and listening stats
- **SpotifyArtist**: Artist information
- **ListeningSession**: Individual listening sessions

### Aggregation
- **DailyAggregation**: Combined daily metrics from all sources

## API Endpoints

### GitHub
- `GET /api/github/stats` - Overall GitHub statistics
- `GET /api/github/contributions` - Daily contributions
- `GET /api/github/repositories` - Repository list
- `GET /api/github/languages` - Language breakdown

### Spotify
- `GET /api/spotify/stats` - Overall listening statistics
- `GET /api/spotify/top-tracks` - Top tracks
- `GET /api/spotify/top-artists` - Top artists
- `GET /api/spotify/listening-history` - Listening history

### Dashboard
- `GET /api/dashboard/overview` - Combined dashboard data
- `GET /api/dashboard/metrics` - Aggregated metrics

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=pipeline --cov=collectors --cov=api
```

## Manual Smoke Checks

These scripts call the real external APIs and are intentionally kept out of `tests/`.

```bash
# Check both collectors
poetry run python scripts/check_collectors.py

# Check one collector only
poetry run python scripts/check_github_collector.py
poetry run python scripts/check_spotify_collector.py
```

## Deployment

### Docker

Build and run the application in Docker:

```bash
docker build -t personal-data-dashboard .
docker run -p 8000:8000 -p 8050:8050 --env-file .env personal-data-dashboard
```

### Railway

Deploy to Railway for free:

1. Create a Railway account at [railway.app](https://railway.app)
2. Connect your GitHub repository
3. Add PostgreSQL service
4. Configure environment variables
5. Deploy!

## Development

### Code Formatting

```bash
# Format code with Black
poetry run black src scripts tests

# Sort imports with isort
poetry run isort src scripts tests

# Check style with flake8
poetry run flake8 src scripts tests
```

### Type Checking

```bash
poetry run mypy src
```

## Roadmap

- [x] Database schema design
- [ ] GitHub data collector
- [ ] Spotify data collector
- [ ] APScheduler integration
- [ ] FastAPI backend
- [ ] Plotly Dash frontend
- [ ] Docker containerization
- [ ] Railway deployment
- [ ] Steam API integration
- [ ] AI-powered insights
- [ ] Email notifications

## License

MIT License - See LICENSE file for details
