# Procfile — process declarations for Railway / Heroku-style deployments
# Railway picks up this file automatically when no railway.toml is present.
# For multi-service deployments, set the start command per service in Railway UI.

web: uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 2
dashboard: gunicorn dashboard.app:server --bind 0.0.0.0:$PORT --workers 2 --timeout 120
