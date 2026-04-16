"""
Unified application launcher for local development.

Usage:
    poetry run python scripts/start_app.py
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

# Add src directory to path for imports when running from source checkout
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline.config import get_settings
from pipeline.database import init_db


ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"


def _build_child_env(settings) -> dict[str, str]:
    """Create a child environment with the project src directory on PYTHONPATH."""
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(SRC_DIR)
        if not existing_pythonpath
        else os.pathsep.join([str(SRC_DIR), existing_pythonpath])
    )
    env.setdefault("API_BASE_URL", f"http://localhost:{settings.effective_port}")
    return env


def _start_process(command: list[str], env: dict[str, str], name: str) -> subprocess.Popen:
    """Start a child process and fail fast if it cannot be created."""
    try:
        return subprocess.Popen(command, cwd=ROOT_DIR, env=env)
    except OSError as exc:
        raise RuntimeError(f"Could not start {name}: {exc}") from exc


def _wait_for_api(base_url: str, timeout_seconds: int = 30) -> bool:
    """Wait for the API health endpoint to respond successfully."""
    deadline = time.time() + timeout_seconds
    health_url = f"{base_url.rstrip('/')}/health"

    while time.time() < deadline:
        try:
            response = requests.get(health_url, timeout=2)
            if response.ok:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)

    return False


def _stop_process(process: subprocess.Popen, name: str) -> None:
    """Terminate a child process gracefully, then force kill if needed."""
    if process.poll() is not None:
        return

    print(f"Stopping {name}...")
    process.terminate()

    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    """Initialize the database and start the API and dashboard together."""
    settings = get_settings()
    env = _build_child_env(settings)
    api_base_url = env["API_BASE_URL"]
    logs_dir = ROOT_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("Personal Data Analytics Dashboard - Start App")
    print("=" * 60)
    print(f"Environment: {settings.environment}")
    print(f"Database: {settings.database_url}")
    print(f"API URL: {api_base_url}")
    print(f"Dashboard URL: http://localhost:{settings.dashboard_port}")

    if not (ROOT_DIR / ".env").exists():
        print("\nWARNING: .env file not found. Copy .env.example to .env before continuing.")

    print("\nInitializing database tables...")
    try:
        init_db()
    except Exception as exc:
        print(f"Failed to initialize database: {exc}")
        return 1

    print("\nStarting API server...")
    api_process = _start_process([sys.executable, "-m", "api.main"], env, "API server")

    if not _wait_for_api(api_base_url):
        print("API did not become ready within 30 seconds.")
        _stop_process(api_process, "API server")
        return 1

    print("Starting dashboard...")
    dashboard_process = _start_process(
        [sys.executable, "-m", "dashboard.app"],
        env,
        "dashboard",
    )

    print("\nApplication is running.")
    print(f"API docs: {api_base_url}/docs")
    print(f"Dashboard: http://localhost:{settings.dashboard_port}")
    print("Press Ctrl+C to stop both processes.")

    try:
        while True:
            api_return_code = api_process.poll()
            dashboard_return_code = dashboard_process.poll()

            if api_return_code is not None:
                print(f"API server exited with code {api_return_code}.")
                _stop_process(dashboard_process, "dashboard")
                return api_return_code

            if dashboard_return_code is not None:
                print(f"Dashboard exited with code {dashboard_return_code}.")
                _stop_process(api_process, "API server")
                return dashboard_return_code

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutdown requested.")
        _stop_process(dashboard_process, "dashboard")
        _stop_process(api_process, "API server")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())