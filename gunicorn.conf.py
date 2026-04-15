"""
Gunicorn configuration for production dashboard serving.
Used by: gunicorn dashboard.app:server -c gunicorn.conf.py
"""
import os

bind = f"0.0.0.0:{os.getenv('PORT', '8050')}"
workers = 2
threads = 2
timeout = 120
keepalive = 5
loglevel = "info"
accesslog = "-"   # stdout
errorlog = "-"    # stderr
preload_app = True
