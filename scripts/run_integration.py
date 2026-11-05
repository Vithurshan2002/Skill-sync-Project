"""Run all three local services together; Ctrl+C stops only these child processes."""
import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import time

import httpx
from dotenv import dotenv_values
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "skill-sync" / "backend"
FRONTEND = ROOT / "skill-sync" / "frontend"
AI = ROOT / "skillsync-ai-model"
RUNTIME = ROOT / ".integration-runtime"
sys.path.insert(0, str(BACKEND))

from app.config import Settings
from app.database import make_engine


def environment(directory):
    values = dotenv_values(directory / ".env")
    # This launch uses the checkout's environment, not inherited DB credentials.
    clean = {key: value for key, value in os.environ.items()
             if not key.startswith(("DB_", "DATABASE_", "AI_", "FASTAPI_", "APP_CONFIG_", "APP_ROUTES_"))}
    clean.update({key: value for key, value in values.items() if value is not None})
    return clean


def preflight():
    backend_env = environment(BACKEND)
    settings = Settings(_env_file=None, **{
        key.lower(): value for key, value in backend_env.items()
        if key.lower() in Settings.model_fields
    })
    engine = make_engine(settings)
    try:
        with engine.connect() as connection:
            labels = set(connection.execute(text("SELECT label FROM categories")).scalars())
            if labels != {"Plumbing", "Electrical", "Carpentry", "Welding"}:
                raise RuntimeError("The isolated database must contain exactly the four model categories.")
    finally:
        engine.dispose()
    front_env = environment(FRONTEND)
    expected_sqlite = FRONTEND / "database" / "integration-testing.sqlite"
    configured = Path(front_env.get("DB_DATABASE", "")).resolve()
    if (front_env.get("DB_CONNECTION") != "sqlite" or configured != expected_sqlite.resolve()
            or front_env.get("DB_URL")):
        raise RuntimeError("Frontend must use its isolated integration-testing.sqlite store.")
    with sqlite3.connect(expected_sqlite.as_uri() + "?mode=ro", uri=True) as connection:
        connection.execute("SELECT 1 FROM sessions LIMIT 1")
    if settings.ai_base_url.rstrip("/") != "http://127.0.0.1:8102" or not settings.ai_enabled:
        raise RuntimeError("Set AI_ENABLED=true and AI_BASE_URL=http://127.0.0.1:8102.")
    if front_env.get("FASTAPI_BASE_URL", "").rstrip("/") != "http://127.0.0.1:8101":
        raise RuntimeError("Set frontend FASTAPI_BASE_URL=http://127.0.0.1:8101.")
    php = os.environ.get("PHP_BINARY") or shutil.which("php")
    if not php:
        php = str(ROOT / "skill-sync" / ".runtime" / "php" / "php.exe")
    ai_python = AI / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    for path in (Path(php), ai_python, FRONTEND / "public" / "build" / "manifest.json"):
        if not path.is_file():
            raise RuntimeError(f"Missing prerequisite: {path}")
    RUNTIME.mkdir(exist_ok=True)
    # Avoid a stale cached configuration pointing at another database.
    front_env.update(APP_CONFIG_CACHE=str(RUNTIME / "frontend-config.php"),
                     APP_ROUTES_CACHE=str(RUNTIME / "frontend-routes.php"))
    return backend_env, front_env, php, ai_python


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate setup without starting servers")
    parser.add_argument("--smoke-test", action="store_true", help="Start, verify readiness, then stop")
    args = parser.parse_args()
    backend_env, front_env, php, ai_python = preflight()
    print("Verified isolated PostgreSQL and frontend stores; four service categories.", flush=True)
    if args.check:
        return
    for port in (8100, 8101, 8102):
        with socket.socket() as check:
            try:
                check.bind(("127.0.0.1", port))
            except OSError:
                raise RuntimeError(f"Port {port} is occupied. No existing process was stopped.") from None
    services = [
        ("ai", [str(ai_python), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8102"],
         AI, environment(AI), "http://127.0.0.1:8102/health"),
        ("backend", [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8101"],
         BACKEND, backend_env, "http://127.0.0.1:8101/health/ready"),
        ("frontend", [php, "-S", "127.0.0.1:8100", "-t", ".", str(
            FRONTEND / "vendor/laravel/framework/src/Illuminate/Foundation/resources/server.php")],
         FRONTEND / "public", front_env, "http://127.0.0.1:8100/"),
    ]
    children = []
    with ExitStack() as stack:
        try:
            with httpx.Client(timeout=3, trust_env=False) as client:
                for name, command, cwd, env, health in services:
                    log = stack.enter_context((RUNTIME / f"{name}.log").open("a", encoding="utf-8"))
                    child = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=log,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                    children.append(child)
                    for _ in range(120):
                        if child.poll() is not None:
                            raise RuntimeError(f"{name} exited; inspect .integration-runtime/{name}.log.")
                        try:
                            if client.get(health).status_code == 200:
                                print(f"{name}: ready", flush=True)
                                break
                        except httpx.HTTPError:
                            pass
                        time.sleep(0.25)
                    else:
                        raise RuntimeError(f"{name} readiness timed out; inspect its log.")
            print("Website: http://127.0.0.1:8100\nBackend docs: http://127.0.0.1:8101/docs\n"
                  "AI docs: http://127.0.0.1:8102/docs\nPress Ctrl+C to stop all three services.", flush=True)
            if not args.smoke_test:
                while all(child.poll() is None for child in children):
                    time.sleep(0.5)
                raise RuntimeError("A service exited; inspect .integration-runtime logs.")
        except KeyboardInterrupt:
            print("Stopping SkillSync services...", flush=True)
        finally:
            for child in reversed(children):
                if child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=5)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except Exception:
        print("Startup failed. Check local .env files, migrations, dependencies, and logs. "
              "Credentials were not displayed.", file=sys.stderr)
        sys.exit(1)
